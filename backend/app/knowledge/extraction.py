import asyncio
import hashlib
import json
import re
import unicodedata
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from fnmatch import fnmatch
from typing import Any

import httpx
from sqlalchemy import func, select

from app.config import Settings
from app.database import Database
from app.knowledge.security import scan_knowledge_text
from app.knowledge.service import KnowledgeService, SearchResult
from app.models import (
    KnowledgeAnalysisScope,
    KnowledgeAnalysisTemplateVersion,
    KnowledgeBlockApplicability,
    KnowledgeBlockVersion,
    KnowledgeCandidateEvidence,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    KnowledgeExtractionTask,
    KnowledgeExtractionTaskDocument,
    KnowledgeExtractionTaskEvent,
    KnowledgeFieldCandidate,
    KnowledgeFieldConflict,
    KnowledgeProcessingVersion,
    KnowledgeSource,
    KnowledgeSourceEntry,
    Task,
    TaskStatus,
)
from app.models.base import utc_now
from app.services.task_service import TaskService


TERMINAL_EXTRACTION_STATUSES = {"review_required", "completed", "failed"}
SUPPORTED_EXTENSIONS = {
    ".csv",
    ".docx",
    ".json",
    ".md",
    ".pdf",
    ".pptx",
    ".txt",
    ".xls",
    ".xlsx",
    ".xml",
    ".yaml",
    ".yml",
}


class ScopedExtractionError(RuntimeError):
    def __init__(
        self,
        code: str,
        stage: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.stage = stage
        self.details = details or {}


def extraction_request_hash(payload: dict[str, Any]) -> str:
    normalized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def extraction_request_id() -> str:
    return str(uuid.uuid4())


def _normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


def _path_root(value: str) -> str:
    return value.replace("\\", "/").strip("/").split("/", 1)[0]


def _code_matches(root: str, code: str) -> bool:
    if not code:
        return False
    return bool(
        re.search(
            rf"(?:^|[^0-9A-Za-z]){re.escape(_normalized(code))}"
            r"(?:$|[^0-9A-Za-z])",
            _normalized(root),
        )
    )


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except ValueError:
        return None


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class CustomerKnowledgeExtractionService:
    def __init__(
        self,
        *,
        database: Database,
        settings: Settings,
        knowledge_service: KnowledgeService,
        task_service: TaskService,
    ) -> None:
        self._database = database
        self._settings = settings
        self._knowledge_service = knowledge_service
        self._task_service = task_service

    async def execute(self, generic_task_id: str) -> None:
        with self._database.session_factory() as session:
            extraction = session.scalar(
                select(KnowledgeExtractionTask).where(
                    KnowledgeExtractionTask.generic_task_id == generic_task_id
                )
            )
            generic_task = session.get(Task, generic_task_id)
            if extraction is None or generic_task is None:
                return
            if extraction.status in TERMINAL_EXTRACTION_STATUSES:
                return
            generic_task.status = TaskStatus.RUNNING
            generic_task.started_at = generic_task.started_at or utc_now()
            extraction.status = "resolving_scope"
            extraction.stage = "resolving_scope"
            self._append_event(
                session,
                extraction,
                "scope.resolution.started",
                {},
            )
            session.commit()

        try:
            async with asyncio.timeout(
                self._settings.knowledge_customer_extraction_timeout_seconds
            ):
                await self._run(extraction.id)
        except ScopedExtractionError as error:
            self._fail(extraction.id, generic_task_id, error)
        except TimeoutError:
            self._fail(
                extraction.id,
                generic_task_id,
                ScopedExtractionError("EXTRACTION_FAILED", "overall_deadline"),
            )
        except Exception:
            self._fail(
                extraction.id,
                generic_task_id,
                ScopedExtractionError("EXTRACTION_FAILED", "internal"),
            )
            raise

    async def _run(self, extraction_id: str) -> None:
        scope_id = self._resolve_scope(extraction_id)
        document_rows = self._prepare_manifest(extraction_id, scope_id)
        requested_fields, schema_registry = self._extraction_contract(extraction_id)

        for ordinal, task_document_id in enumerate(document_rows, start=1):
            await self._extract_document(
                extraction_id,
                task_document_id,
                requested_fields,
                schema_registry,
                ordinal,
                len(document_rows),
            )
        self._aggregate(extraction_id)

    def _resolve_scope(self, extraction_id: str) -> str:
        with self._database.session_factory() as session:
            task = session.get(KnowledgeExtractionTask, extraction_id)
            if task is None:
                raise ScopedExtractionError("EXTRACTION_FAILED", "resolving_scope")
            request = task.request_json
            source = session.get(KnowledgeSource, task.source_id)
            if source is None:
                raise ScopedExtractionError(
                    "KNOWLEDGE_SOURCE_NOT_FOUND", "resolving_scope"
                )
            subject = request["subject"]
            entries = list(
                session.scalars(
                    select(KnowledgeSourceEntry).where(
                        KnowledgeSourceEntry.source_id == source.id
                    )
                )
            )
            roots = sorted(
                {
                    _path_root(item.relative_path)
                    for item in entries
                    if _path_root(item.relative_path)
                }
                | (
                    {_path_root(source.subpath)}
                    if source.subpath and _path_root(source.subpath)
                    else set()
                )
            )
            identities = [
                subject.get("official_name", ""),
                subject.get("short_name", ""),
                *subject.get("aliases", []),
            ]
            normalized_identities = {
                _normalized(str(value)) for value in identities if value and str(value).strip()
            }
            candidates: list[tuple[int, str, list[str]]] = []
            for root in roots:
                matched_by: list[str] = []
                score = 0
                if _code_matches(root, subject.get("code", "")):
                    matched_by.append("organization_code")
                    score += 100
                normalized_root = _normalized(root)
                for identity in normalized_identities:
                    if identity and identity in normalized_root:
                        matched_by.append(
                            "official_name"
                            if identity == _normalized(subject.get("official_name", ""))
                            else "name_or_alias"
                        )
                        score += 10
                if matched_by:
                    candidates.append((score, root, list(dict.fromkeys(matched_by))))
            if not candidates:
                raise ScopedExtractionError("SCOPE_NOT_FOUND", "resolving_scope")
            best_score = max(item[0] for item in candidates)
            best = [item for item in candidates if item[0] == best_score]
            if len(best) != 1:
                raise ScopedExtractionError(
                    "SCOPE_AMBIGUOUS",
                    "resolving_scope",
                    details={"candidates": [item[1] for item in best]},
                )
            _, root, matched_by = best[0]
            prefix = f"{root}/"
            active = session.scalar(
                select(KnowledgeAnalysisScope)
                .where(
                    KnowledgeAnalysisScope.source_id == source.id,
                    KnowledgeAnalysisScope.external_system
                    == subject["external_system"],
                    KnowledgeAnalysisScope.external_subject_id
                    == subject["external_id"],
                    KnowledgeAnalysisScope.valid_to.is_(None),
                )
                .order_by(KnowledgeAnalysisScope.revision.desc())
            )
            if active is not None and active.canonical_prefix == prefix:
                scope = active
            else:
                revision = 1
                supersedes_id = None
                if active is not None:
                    active.valid_to = utc_now()
                    revision = active.revision + 1
                    supersedes_id = active.id
                scope = KnowledgeAnalysisScope(
                    source_id=source.id,
                    subject_type=subject["type"],
                    external_system=subject["external_system"],
                    external_subject_id=subject["external_id"],
                    canonical_prefix=prefix,
                    matched_by=matched_by,
                    confidence=1.0 if "organization_code" in matched_by else 0.9,
                    revision=revision,
                    supersedes_id=supersedes_id,
                )
                session.add(scope)
                session.flush()
            task.scope_id = scope.id
            task.status = "preparing_documents"
            task.stage = "preparing_documents"
            self._append_event(
                session,
                task,
                "scope.resolved",
                {
                    "scope_id": scope.id,
                    "canonical_prefix": prefix,
                    "matched_by": matched_by,
                },
            )
            session.commit()
            return scope.id

    def _prepare_manifest(self, extraction_id: str, scope_id: str) -> list[str]:
        with self._database.session_factory() as session:
            task = session.get(KnowledgeExtractionTask, extraction_id)
            scope = session.get(KnowledgeAnalysisScope, scope_id)
            if task is None or scope is None:
                raise ScopedExtractionError(
                    "EXTRACTION_FAILED", "preparing_documents"
                )
            existing_rows = list(
                session.scalars(
                    select(KnowledgeExtractionTaskDocument)
                    .where(
                        KnowledgeExtractionTaskDocument.extraction_task_id
                        == task.id
                    )
                    .order_by(KnowledgeExtractionTaskDocument.canonical_path)
                )
            )
            if existing_rows:
                task.status = "extracting"
                task.stage = "extracting"
                session.commit()
                return [item.id for item in existing_rows]
            source = session.get(KnowledgeSource, scope.source_id)
            source_subpath = (source.subpath or "").replace("\\", "/").strip("/")
            scope_prefix = scope.canonical_prefix.strip("/")
            local_prefix = (
                ""
                if source_subpath == scope_prefix
                else scope_prefix.removeprefix(f"{source_subpath}/")
                if source_subpath and scope_prefix.startswith(f"{source_subpath}/")
                else scope_prefix
            )
            query = select(KnowledgeSourceEntry).where(
                KnowledgeSourceEntry.source_id == scope.source_id
            )
            if local_prefix:
                query = query.where(
                    KnowledgeSourceEntry.relative_path.startswith(f"{local_prefix}/")
                )
            entries = list(
                session.scalars(query.order_by(KnowledgeSourceEntry.relative_path))
            )
            if not entries:
                raise ScopedExtractionError("SCOPE_NOT_FOUND", "preparing_documents")
            created: list[str] = []
            ready_count = 0
            for entry in entries:
                if entry.entry_kind == "directory":
                    continue
                relative_path = entry.relative_path.replace("\\", "/")
                path = "/".join(
                    value
                    for value in (source_subpath, relative_path)
                    if value
                )
                filename = path.rsplit("/", 1)[-1]
                document = session.scalar(
                    select(KnowledgeDocument).where(
                        KnowledgeDocument.source_entry_id == entry.id
                    )
                )
                status, excluded_reason = self._manifest_status(
                    entry, document, filename
                )
                document_version = None
                processing_version = None
                if document is not None and status in {
                    "ready",
                    "processing_upgrade_required",
                }:
                    document_version, processing_version = self._ensure_versions(
                        session, entry, document
                    )
                    status = "ready"
                row = KnowledgeExtractionTaskDocument(
                    extraction_task_id=task.id,
                    source_entry_id=entry.id,
                    document_id=document.id if document is not None else None,
                    document_version_id=(
                        document_version.id if document_version is not None else None
                    ),
                    processing_version_id=(
                        processing_version.id if processing_version is not None else None
                    ),
                    canonical_path=path,
                    manifest_status=status,
                    extraction_status=("excluded" if excluded_reason else "pending"),
                    excluded_reason=excluded_reason,
                )
                session.add(row)
                session.flush()
                created.append(row.id)
                ready_count += status == "ready"
            task.status = "extracting"
            task.stage = "extracting"
            self._append_event(
                session,
                task,
                "manifest.completed",
                {
                    "total_documents": len(created),
                    "ready_documents": ready_count,
                },
            )
            session.commit()
            return created

    @staticmethod
    def _manifest_status(
        entry: KnowledgeSourceEntry,
        document: KnowledgeDocument | None,
        filename: str,
    ) -> tuple[str, str | None]:
        if filename.startswith("~$"):
            return "excluded", "temporary_office_file"
        if entry.extension.casefold() not in SUPPORTED_EXTENSIONS:
            return "unsupported_extension", "unsupported_extension"
        if not entry.present:
            return "source_absent", "source_absent"
        if entry.processing_status in {"failed", "extraction_failed"}:
            return "extraction_failed", None
        if entry.processing_mode == "metadata_only" or entry.processing_status == "metadata_only":
            return "metadata_only", None
        if document is None:
            return "observed_only", None
        if entry.content_hash and entry.content_hash != document.content_hash:
            return "source_changed", None
        if (
            entry.processor_fingerprint
            and entry.processor_fingerprint != document.processor_fingerprint
        ):
            return "processing_upgrade_required", None
        return "ready", None

    def _ensure_versions(
        self,
        session,
        entry: KnowledgeSourceEntry,
        document: KnowledgeDocument,
    ) -> tuple[KnowledgeDocumentVersion, KnowledgeProcessingVersion]:
        raw_hash = entry.raw_content_hash or entry.content_hash or document.content_hash
        version = session.scalar(
            select(KnowledgeDocumentVersion).where(
                KnowledgeDocumentVersion.document_id == document.id,
                KnowledgeDocumentVersion.raw_content_hash == raw_hash,
            )
        )
        if version is None:
            version = KnowledgeDocumentVersion(
                document_id=document.id,
                source_entry_id=entry.id,
                source_generation_id=document.generation_ingestion_id,
                canonical_path=document.canonical_path,
                raw_content_hash=raw_hash,
                content_hash=document.content_hash,
                source_modified_at=entry.modified_at,
            )
            session.add(version)
            session.flush()
        fingerprint = (
            document.processor_fingerprint
            or entry.processor_fingerprint
            or "legacy-processor"
        )
        processing = session.scalar(
            select(KnowledgeProcessingVersion).where(
                KnowledgeProcessingVersion.document_version_id == version.id,
                KnowledgeProcessingVersion.processor_fingerprint == fingerprint,
            )
        )
        if processing is None:
            active = session.scalar(
                select(KnowledgeProcessingVersion).where(
                    KnowledgeProcessingVersion.document_version_id == version.id,
                    KnowledgeProcessingVersion.status == "active",
                )
            )
            processing = KnowledgeProcessingVersion(
                document_version_id=version.id,
                processor_fingerprint=fingerprint,
                extractor_version=entry.extractor_version,
                status="active",
                quality_result={"passed": True, "source": "existing_index"},
                supersedes_id=active.id if active is not None else None,
                activated_at=utc_now(),
            )
            if active is not None:
                active.status = "superseded"
            session.add(processing)
            session.flush()
        return version, processing

    def _extraction_contract(
        self, extraction_id: str
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        with self._database.session_factory() as session:
            task = session.get(KnowledgeExtractionTask, extraction_id)
            if task is None:
                return [], {}
            template = session.get(
                KnowledgeAnalysisTemplateVersion, task.template_version_id
            )
            return (
                list(task.request_json["requested_fields"]),
                dict(template.schema_registry) if template is not None else {},
            )

    async def _extract_document(
        self,
        extraction_id: str,
        task_document_id: str,
        requested_fields: list[dict[str, Any]],
        schema_registry: dict[str, Any],
        ordinal: int,
        total: int,
    ) -> None:
        with self._database.session_factory() as session:
            task_document = session.get(
                KnowledgeExtractionTaskDocument, task_document_id
            )
            if task_document is None:
                return
            if task_document.extraction_status in {"excluded", "analyzed"}:
                return
            if task_document.manifest_status != "ready" or not task_document.document_id:
                task_document.extraction_status = "failed"
                task_document.failure_code = self._failure_for_manifest(
                    task_document.manifest_status
                )
                session.commit()
                return
            task_document.extraction_status = "extracting"
            task_document.checkpoint = {"batch": 0, "status": "started"}
            session.commit()

        results = self._knowledge_service.document_results(task_document.document_id)
        if not results:
            with self._database.session_factory() as session:
                row = session.get(KnowledgeExtractionTaskDocument, task_document_id)
                if row:
                    row.extraction_status = "failed"
                    row.failure_code = "EMPTY_TEXT"
                    session.commit()
            return
        try:
            async with asyncio.timeout(
                self._settings.knowledge_customer_document_timeout_seconds
            ):
                fields, validation_errors = (
                    await self._knowledge_service.extract_customer_fields(
                        requested_fields=requested_fields,
                        results=results,
                        schema_registry=schema_registry,
                    )
                )
        except Exception as error:
            failure_code = (
                "MODEL_TIMEOUT"
                if isinstance(error, (TimeoutError, httpx.TimeoutException))
                else "EXTRACTION_FAILED"
            )
            with self._database.session_factory() as session:
                task = session.get(KnowledgeExtractionTask, extraction_id)
                row = session.get(
                    KnowledgeExtractionTaskDocument, task_document_id
                )
                if task is not None and row is not None:
                    row.extraction_status = "failed"
                    row.failure_code = failure_code
                    row.checkpoint = {
                        "batch": 0,
                        "status": "failed",
                        "failure_code": failure_code,
                    }
                    self._append_event(
                        session,
                        task,
                        "document.extraction_failed",
                        {
                            "task_document_id": row.id,
                            "processed": ordinal,
                            "total": total,
                            "failure_code": failure_code,
                        },
                    )
                    session.commit()
            return
        by_chunk = {item.id: item for item in results}
        with self._database.session_factory() as session:
            task = session.get(KnowledgeExtractionTask, extraction_id)
            row = session.get(KnowledgeExtractionTaskDocument, task_document_id)
            if task is None or row is None:
                return
            for field in fields:
                serialized = json.dumps(field["value"], ensure_ascii=False)
                secret_scan = scan_knowledge_text(serialized)
                if secret_scan.secret_detected:
                    validation_errors.append(
                        {"field_code": field["field_code"], "reasons": ["secret_detected"]}
                    )
                    continue
                candidate = KnowledgeFieldCandidate(
                    extraction_task_id=task.id,
                    field_code=field["field_code"],
                    value_json=field["value"],
                    option_external_id=field["option_id"],
                    confidence=field["confidence"],
                    effective_from=_parse_datetime(field.get("effective_from")),
                    effective_to=_parse_datetime(field.get("effective_to")),
                    aggregation_status="file_candidate",
                )
                session.add(candidate)
                session.flush()
                evidence_json: list[dict[str, Any]] = []
                for chunk_id in field["evidence_chunk_ids"]:
                    result = by_chunk[chunk_id]
                    chunk_location = self._chunk_location(
                        session, chunk_id, result.text
                    )
                    excerpt = scan_knowledge_text(result.text[:500]).safe_text
                    evidence = KnowledgeCandidateEvidence(
                        candidate_id=candidate.id,
                        document_id=row.document_id,
                        document_version_id=row.document_version_id,
                        chunk_id=chunk_id,
                        resource_uri=result.resource_uri,
                        canonical_path=row.canonical_path,
                        location=chunk_location,
                        excerpt=excerpt,
                    )
                    session.add(evidence)
                    evidence_json.append(
                        {
                            "chunk_id": chunk_id,
                            "document_id": row.document_id,
                            "document_version_id": row.document_version_id,
                        }
                    )
                block = KnowledgeBlockVersion(
                    processing_version_id=row.processing_version_id,
                    subject_external_system=task.request_json["subject"]["external_system"],
                    subject_external_id=task.subject_external_id,
                    fact_key=field["field_code"],
                    value_json=field["value"],
                    evidence_json=evidence_json,
                )
                session.add(block)
                session.flush()
                candidate.block_version_id = block.id
                session.add(
                    KnowledgeBlockApplicability(
                        block_version_id=block.id,
                        effective_from=_parse_datetime(field.get("effective_from")),
                        effective_to=_parse_datetime(field.get("effective_to")),
                        change_reason="extracted_from_document_evidence",
                        audit_json={"extraction_task_id": task.id},
                    )
                )
            row.extraction_status = "analyzed"
            row.checkpoint = {
                "batch": 1,
                "status": "completed",
                "validation_errors": validation_errors,
            }
            self._append_event(
                session,
                task,
                "document.extracted",
                {
                    "task_document_id": row.id,
                    "processed": ordinal,
                    "total": total,
                    "candidate_count": len(fields),
                    "validation_error_count": len(validation_errors),
                },
            )
            session.commit()

    @staticmethod
    def _failure_for_manifest(status: str) -> str:
        return {
            "metadata_only": "METADATA_ONLY",
            "observed_only": "NOT_INGESTED",
            "source_changed": "SOURCE_CHANGED",
            "extraction_failed": "EXTRACTION_FAILED",
        }.get(status, "INGESTION_REQUIRED")

    @staticmethod
    def _chunk_location(
        session,
        chunk_id: str,
        text: str,
    ) -> dict[str, Any]:
        from app.models import KnowledgeChunk

        chunk = session.get(KnowledgeChunk, chunk_id)
        metadata = dict(chunk.metadata_json) if chunk is not None else {}
        allowed = {
            "sheet",
            "cell",
            "cell_range",
            "page",
            "section",
            "heading",
            "table",
        }
        location = {
            key: value for key, value in metadata.items() if key in allowed
        }
        sheet_match = re.search(r"\[sheet\][^\n]*\bname=([^\s]+)", text)
        cell_match = re.search(r"(?m)^([A-Z]{1,3}[1-9][0-9]*)\t", text)
        page_match = re.search(r"\[page\]\s+index=([1-9][0-9]*)", text)
        if sheet_match and "sheet" not in location:
            location["sheet"] = sheet_match.group(1)
        if cell_match and "cell_range" not in location:
            location["cell_range"] = cell_match.group(1)
        if page_match and "page" not in location:
            location["page"] = int(page_match.group(1))
        return location

    def _aggregate(self, extraction_id: str) -> None:
        with self._database.session_factory() as session:
            task = session.get(KnowledgeExtractionTask, extraction_id)
            if task is None:
                return
            task.status = "aggregating"
            task.stage = "aggregating"
            self._append_event(session, task, "aggregation.started", {})
            session.flush()
            candidates = list(
                session.scalars(
                    select(KnowledgeFieldCandidate).where(
                        KnowledgeFieldCandidate.extraction_task_id == task.id
                    )
                )
            )
            evidence = list(
                session.scalars(
                    select(KnowledgeCandidateEvidence)
                    .join(
                        KnowledgeFieldCandidate,
                        KnowledgeFieldCandidate.id
                        == KnowledgeCandidateEvidence.candidate_id,
                    )
                    .where(KnowledgeFieldCandidate.extraction_task_id == task.id)
                )
            )
            evidence_by_candidate: dict[str, list[KnowledgeCandidateEvidence]] = defaultdict(list)
            for item in evidence:
                evidence_by_candidate[item.candidate_id].append(item)
            template = session.get(
                KnowledgeAnalysisTemplateVersion, task.template_version_id
            )
            grouped: dict[str, list[KnowledgeFieldCandidate]] = defaultdict(list)
            as_of = _parse_datetime(
                task.request_json["analysis_context"]["as_of"]
            )
            applicability_exclusions: list[dict[str, Any]] = []
            for candidate in candidates:
                effective_from = _as_utc(candidate.effective_from)
                effective_to = _as_utc(candidate.effective_to)
                applicable = (
                    (effective_from is None or effective_from <= as_of)
                    and (effective_to is None or as_of < effective_to)
                )
                if applicable:
                    grouped[candidate.field_code].append(candidate)
                else:
                    candidate.aggregation_status = "excluded_outside_as_of"
                    applicability_exclusions.append(
                        {
                            "candidate_id": candidate.id,
                            "block_version_id": candidate.block_version_id,
                            "field_code": candidate.field_code,
                            "reason_code": "OUTSIDE_ANALYSIS_AS_OF",
                            "effective_from": (
                                effective_from.isoformat()
                                if effective_from is not None
                                else None
                            ),
                            "effective_to": (
                                effective_to.isoformat()
                                if effective_to is not None
                                else None
                            ),
                        }
                    )
            output_candidates: list[dict[str, Any]] = []
            conflicts: list[dict[str, Any]] = []
            requested_codes = {
                item["code"] for item in task.request_json["requested_fields"]
            }
            resolved_codes: set[str] = set()
            minimum_confidence = float(
                task.request_json["result_policy"]["minimum_confidence"]
            )
            for field_code, items in grouped.items():
                value_groups: dict[str, list[KnowledgeFieldCandidate]] = defaultdict(list)
                for item in items:
                    value_groups[
                        json.dumps(item.value_json, ensure_ascii=False, sort_keys=True)
                    ].append(item)
                ranked: list[tuple[int, str, list[KnowledgeFieldCandidate]]] = []
                for value_key, value_items in value_groups.items():
                    priority = min(
                        self._source_priority(
                            template,
                            evidence_by_candidate[item.id],
                        )
                        for item in value_items
                    )
                    ranked.append((priority, value_key, value_items))
                best_priority = min(item[0] for item in ranked)
                best = [item for item in ranked if item[0] == best_priority]
                if len(best) > 1:
                    ids = [candidate.id for _, _, values in best for candidate in values]
                    conflict = KnowledgeFieldConflict(
                        extraction_task_id=task.id,
                        field_code=field_code,
                        candidate_ids=ids,
                        reason_code="SAME_PRIORITY_DIFFERENT_VALUES",
                    )
                    session.add(conflict)
                    session.flush()
                    conflicts.append(
                        {
                            "id": conflict.id,
                            "field_code": field_code,
                            "candidate_ids": ids,
                            "reason_code": conflict.reason_code,
                        }
                    )
                for _priority, _value_key, value_items in best:
                    winner = max(value_items, key=lambda item: item.confidence)
                    if winner.confidence < minimum_confidence:
                        continue
                    winner.aggregation_status = (
                        "conflict" if len(best) > 1 else "selected"
                    )
                    resolved_codes.add(field_code)
                    unique_evidence: dict[tuple[str, str], KnowledgeCandidateEvidence] = {}
                    for item in value_items:
                        for citation in evidence_by_candidate[item.id]:
                            unique_evidence[(citation.chunk_id, citation.document_version_id)] = citation
                    output_candidates.append(
                        {
                            "id": winner.id,
                            "block_version_id": winner.block_version_id,
                            "field_code": field_code,
                            "value": winner.value_json,
                            "option_id": winner.option_external_id,
                            "confidence": max(item.confidence for item in value_items),
                            "effective_from": (
                                _as_utc(winner.effective_from).isoformat()
                                if winner.effective_from is not None
                                else None
                            ),
                            "effective_to": (
                                _as_utc(winner.effective_to).isoformat()
                                if winner.effective_to is not None
                                else None
                            ),
                            "evidence": [
                                self._evidence_response(item)
                                for item in unique_evidence.values()
                            ],
                        }
                    )
            documents = list(
                session.scalars(
                    select(KnowledgeExtractionTaskDocument).where(
                        KnowledgeExtractionTaskDocument.extraction_task_id == task.id
                    )
                )
            )
            excluded = sum(item.extraction_status == "excluded" for item in documents)
            analyzed = sum(item.extraction_status == "analyzed" for item in documents)
            failed = sum(item.extraction_status == "failed" for item in documents)
            denominator = len(documents) - excluded
            coverage_rate = analyzed / denominator if denominator else 1.0
            unresolved = [
                {"field_code": code, "reason_code": "EVIDENCE_NOT_FOUND"}
                for code in sorted(requested_codes - resolved_codes)
            ]
            status = "review_required" if output_candidates or conflicts else "completed"
            error_code = "EXTRACTION_PARTIAL" if failed else None
            task.status = status
            task.stage = status
            task.error_code = error_code
            task.completed_at = utc_now()
            scope = session.get(KnowledgeAnalysisScope, task.scope_id)
            source = session.get(KnowledgeSource, task.source_id)
            result = {
                "id": task.id,
                "schema_version": 1,
                "status": status,
                "subject_external_id": task.subject_external_id,
                "scope": {
                    "id": scope.id,
                    "source_id": scope.source_id,
                    "canonical_prefix": scope.canonical_prefix,
                    "confidence": scope.confidence,
                },
                "coverage": {
                    "total_documents": len(documents),
                    "ready_documents": sum(
                        item.manifest_status == "ready" for item in documents
                    ),
                    "analyzed_documents": analyzed,
                    "failed_documents": failed,
                    "excluded_documents": excluded,
                    "coverage_rate": round(coverage_rate, 6),
                },
                "field_candidates": output_candidates,
                "conflicts": conflicts,
                "unresolved_fields": unresolved,
                "applicability_exclusions": applicability_exclusions,
                "document_failures": [
                    {
                        "document_id": item.document_id,
                        "canonical_path": item.canonical_path,
                        "reason_code": item.failure_code,
                        "retryable": item.manifest_status
                        not in {"unsupported_extension", "source_absent"},
                    }
                    for item in documents
                    if item.extraction_status == "failed"
                ],
                "versions": {
                    "source_generation_id": max(
                        (
                            version.source_generation_id or ""
                            for version in session.scalars(
                                select(KnowledgeDocumentVersion).where(
                                    KnowledgeDocumentVersion.id.in_(
                                        [
                                            item.document_version_id
                                            for item in documents
                                            if item.document_version_id
                                        ]
                                    )
                                )
                            )
                        ),
                        default="",
                    )
                    or None,
                    "analysis_template_code": template.code,
                    "analysis_template_version": template.version,
                    "extractor_version": template.extractor_version,
                    "model_id": self._settings.ollama_memory_model,
                    "source_id": source.id,
                },
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat(),
                "error_code": error_code,
            }
            task.result_json = result
            generic = session.get(Task, task.generic_task_id)
            if generic is not None:
                generic.status = TaskStatus.COMPLETED
                generic.final_report = result
                generic.completed_at = task.completed_at
            self._append_event(
                session,
                task,
                "aggregation.completed",
                {
                    "candidate_count": len(output_candidates),
                    "conflict_count": len(conflicts),
                    "coverage_rate": coverage_rate,
                    "failed_documents": failed,
                },
            )
            session.commit()

    @staticmethod
    def _source_priority(
        template: KnowledgeAnalysisTemplateVersion,
        evidence: list[KnowledgeCandidateEvidence],
    ) -> int:
        paths = [item.canonical_path for item in evidence]
        for rule in template.source_priorities:
            pattern = str(rule.get("pattern", "*"))
            if pattern == "*" or any(
                pattern in path or fnmatch(path, pattern) for path in paths
            ):
                return int(rule.get("priority", 100))
        return 100

    @staticmethod
    def _evidence_response(item: KnowledgeCandidateEvidence) -> dict[str, Any]:
        location = item.location
        return {
            "document_id": item.document_id,
            "document_version_id": item.document_version_id,
            "chunk_id": item.chunk_id,
            "resource_uri": item.resource_uri,
            "canonical_path": item.canonical_path,
            "sheet": location.get("sheet"),
            "cell_range": location.get("cell_range") or location.get("cell"),
            "page": location.get("page"),
            "section": location.get("section") or location.get("heading"),
            "excerpt": item.excerpt,
        }

    def _append_event(
        self,
        session,
        task: KnowledgeExtractionTask,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        sequence = session.scalar(
            select(func.max(KnowledgeExtractionTaskEvent.sequence)).where(
                KnowledgeExtractionTaskEvent.extraction_task_id == task.id
            )
        )
        session.add(
            KnowledgeExtractionTaskEvent(
                extraction_task_id=task.id,
                sequence=int(sequence or 0) + 1,
                stage=task.stage,
                event_type=event_type,
                data=data,
            )
        )

    def _fail(
        self,
        extraction_id: str,
        generic_task_id: str,
        error: ScopedExtractionError,
    ) -> None:
        with self._database.session_factory() as session:
            task = session.get(KnowledgeExtractionTask, extraction_id)
            generic = session.get(Task, generic_task_id)
            if task is not None:
                task.status = "failed"
                task.stage = "failed"
                task.error_code = error.code
                task.error_details = error.details
                task.completed_at = utc_now()
                task.result_json = {
                    "id": task.id,
                    "schema_version": 1,
                    "status": "failed",
                    "subject_external_id": task.subject_external_id,
                    "error": {
                        "code": error.code,
                        "stage": error.stage,
                        "details": error.details,
                    },
                    "created_at": task.created_at.isoformat(),
                    "completed_at": task.completed_at.isoformat(),
                }
                self._append_event(
                    session,
                    task,
                    "extraction.failed",
                    {"error_code": error.code, "stage": error.stage},
                )
            if generic is not None:
                generic.status = TaskStatus.FAILED
                generic.error = error.code
                generic.completed_at = utc_now()
            session.commit()
