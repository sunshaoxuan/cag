import asyncio
import hashlib
import json
import re
import time
import unicodedata
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from fnmatch import fnmatch
from typing import Any

import httpx
from sqlalchemy import func, select

from app.config import Settings
from app.database import Database
from app.knowledge.security import scan_knowledge_text
from app.knowledge.extractors import SUPPORTED_EXTENSIONS
from app.knowledge.path_policy import is_historical_path
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
    KnowledgeIngestion,
    KnowledgeProcessingVersion,
    KnowledgeSource,
    KnowledgeSourceEntry,
    Task,
    TaskStatus,
)
from app.models.base import utc_now
from app.services.task_service import TaskService


TERMINAL_EXTRACTION_STATUSES = {
    "review_required",
    "completed",
    "failed",
    "cancelled",
}
CUSTOMIZATION_DIRECTORIES = {
    "2.カスタマイズ情報",
    "2.カスタイズ情報",
}
REMOTE_INFORMATION_DIRECTORIES = {
    "6.リモート接続情報",
}
SPECIAL_LEDGER_FIELDS = {"customizations", "vpns", "environments"}
def requested_fields_for_document(
    canonical_path: str,
    requested_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if is_historical_path(canonical_path) or canonical_path.casefold().endswith(
        ".lnk"
    ):
        return []
    segments = {
        re.sub(r"\s+", "", _normalized(segment))
        for segment in canonical_path.replace("\\", "/").split("/")
    }
    if segments & CUSTOMIZATION_DIRECTORIES:
        allowed = {"customizations"}
    elif segments & REMOTE_INFORMATION_DIRECTORIES:
        allowed = {"vpns", "environments"}
    else:
        allowed = {str(item["code"]) for item in requested_fields} - (
            SPECIAL_LEDGER_FIELDS
        )
    return [item for item in requested_fields if str(item["code"]) in allowed]


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
            await self._run(extraction.id)
        except asyncio.CancelledError:
            self.cancel(extraction.id, generic_task_id)
            raise
        except ScopedExtractionError as error:
            self._fail(extraction.id, generic_task_id, error)
        except Exception:
            self._fail(
                extraction.id,
                generic_task_id,
                ScopedExtractionError("EXTRACTION_FAILED", "internal"),
            )
            raise

    async def _run(self, extraction_id: str) -> None:
        scope_id = self._resolve_scope(extraction_id)
        with self._database.session_factory() as session:
            scope = session.get(KnowledgeAnalysisScope, scope_id)
            if scope is None:
                raise ScopedExtractionError(
                    "SCOPE_NOT_FOUND",
                    "resolving_scope",
                )
            source_id = scope.source_id
        lease_owner = f"extraction:{scope_id}:{extraction_id}"
        while not self._knowledge_service.acquire_source_lease(
            source_id,
            lease_owner,
        ):
            await asyncio.sleep(1)
        try:
            await self._prepare_required_versions(extraction_id, scope_id)
            document_rows = self._prepare_manifest(extraction_id, scope_id)
            requested_fields, schema_registry = self._extraction_contract(
                extraction_id
            )

            for ordinal, task_document_id in enumerate(document_rows, start=1):
                self._knowledge_service.renew_source_lease(
                    source_id,
                    lease_owner,
                )
                await self._extract_document(
                    extraction_id,
                    task_document_id,
                    requested_fields,
                    schema_registry,
                    ordinal,
                    len(document_rows),
                )
            self._aggregate(extraction_id)
        finally:
            self._knowledge_service.release_source_lease(
                source_id,
                lease_owner,
            )

    async def _prepare_required_versions(
        self,
        extraction_id: str,
        scope_id: str,
    ) -> None:
        with self._database.session_factory() as session:
            task = session.get(KnowledgeExtractionTask, extraction_id)
            scope = session.get(KnowledgeAnalysisScope, scope_id)
            if task is None or scope is None:
                raise ScopedExtractionError(
                    "EXTRACTION_FAILED",
                    "preparing_versions",
                )
            policy = dict(task.request_json.get("ingestion_policy") or {})
            if policy.get("mode") != "prepare_required_versions":
                return
            source = session.get(KnowledgeSource, scope.source_id)
            if source is None:
                raise ScopedExtractionError(
                    "KNOWLEDGE_SOURCE_NOT_FOUND",
                    "preparing_versions",
                )
            source_subpath = (source.subpath or "").replace("\\", "/").strip("/")
            scope_prefix = scope.canonical_prefix.strip("/")
            local_prefix = (
                ""
                if scope_prefix == source_subpath
                else scope_prefix.removeprefix(f"{source_subpath}/")
                if source_subpath and scope_prefix.startswith(f"{source_subpath}/")
                else scope_prefix
            )
            task.status = "preparing_versions"
            task.stage = "preparing_versions"
            session.commit()

        retry_statuses = ["observed", "metadata_only", "empty_text"]
        if policy.get("retry_failed_documents", True):
            retry_statuses.append("failed")
        ingestion, created = self._knowledge_service.create_ingestion(
            scope.source_id,
            trigger="scope_repair",
            analysis_scope_id=scope.id,
            scope_prefix=local_prefix,
            retry_statuses=retry_statuses,
            enqueue=False,
        )
        with self._database.session_factory() as session:
            task = session.get(KnowledgeExtractionTask, extraction_id)
            if task is not None:
                self._append_event(
                    session,
                    task,
                    "scope.ingestion.started",
                    {
                        "ingestion_id": ingestion.id,
                        "created": created,
                        "scope_prefix": local_prefix,
                    },
                )
                session.commit()

        if created:
            await self._knowledge_service.ingest(ingestion.id)
        while True:
            with self._database.session_factory() as session:
                current = session.get(KnowledgeIngestion, ingestion.id)
                if current is None:
                    raise ScopedExtractionError(
                        "INGESTION_PREPARATION_FAILED",
                        "preparing_versions",
                    )
                current_status = current.status
                result = {
                    "ingestion_id": current.id,
                    "status": current.status,
                    "files_seen": current.files_seen,
                    "chunks_written": current.chunks_written,
                    "rejected_files": current.rejected_files,
                    "skipped_files": current.skipped_files,
                }
            if current_status in {"completed", "failed", "cancelled"}:
                break
            await asyncio.sleep(1)
        if current_status != "completed":
            raise ScopedExtractionError(
                "INGESTION_PREPARATION_FAILED",
                "preparing_versions",
                details=result,
            )
        with self._database.session_factory() as session:
            task = session.get(KnowledgeExtractionTask, extraction_id)
            if task is not None:
                self._append_event(
                    session,
                    task,
                    "scope.ingestion.completed",
                    result,
                )
                session.commit()

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
                document = self._current_document(session, entry)
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
    def _current_document(
        session,
        entry: KnowledgeSourceEntry,
    ) -> KnowledgeDocument | None:
        return session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.source_entry_id == entry.id,
                KnowledgeDocument.canonical_path == entry.relative_path,
            )
        )

    @staticmethod
    def _manifest_status(
        entry: KnowledgeSourceEntry,
        document: KnowledgeDocument | None,
        filename: str,
    ) -> tuple[str, str | None]:
        if is_historical_path(entry.relative_path):
            return "excluded", "historical_path"
        if filename.startswith("~$"):
            return "excluded", "temporary_office_file"
        if not entry.present:
            return "source_absent", "source_absent"
        if entry.processing_status in {"failed", "extraction_failed"}:
            return "extraction_failed", None
        if entry.processing_mode == "path_only":
            return ("ready", None) if document is not None else ("observed_only", None)
        if entry.extension.casefold() not in SUPPORTED_EXTENSIONS:
            return "unsupported_extension", "unsupported_extension"
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
            if task_document.extraction_status == "analyzed":
                return
            if task_document.extraction_status == "excluded":
                if task_document.checkpoint.get("status") == "excluded":
                    return
                task = session.get(KnowledgeExtractionTask, extraction_id)
                task_document.checkpoint = {
                    "batch": 0,
                    "status": "excluded",
                    "reason_code": task_document.excluded_reason,
                }
                if task is not None:
                    self._append_event(
                        session,
                        task,
                        "document.excluded",
                        {
                            "task_document_id": task_document.id,
                            "processed": ordinal,
                            "total": total,
                            "reason_code": task_document.excluded_reason,
                        },
                    )
                session.commit()
                return
            if task_document.manifest_status != "ready" or not task_document.document_id:
                if task_document.checkpoint.get("status") == "failed":
                    return
                task = session.get(KnowledgeExtractionTask, extraction_id)
                task_document.extraction_status = "failed"
                task_document.failure_code = self._failure_for_manifest(
                    task_document.manifest_status
                )
                task_document.checkpoint = {
                    "batch": 0,
                    "status": "failed",
                    "failure_code": task_document.failure_code,
                }
                if task is not None:
                    self._append_event(
                        session,
                        task,
                        "document.extraction_failed",
                        {
                            "task_document_id": task_document.id,
                            "processed": ordinal,
                            "total": total,
                            "failure_code": task_document.failure_code,
                        },
                    )
                session.commit()
                return
            task_document.extraction_status = "extracting"
            task_document.checkpoint = {"batch": 0, "status": "started"}
            session.commit()

        results = self._knowledge_service.document_results(task_document.document_id)
        if not results:
            with self._database.session_factory() as session:
                task = session.get(KnowledgeExtractionTask, extraction_id)
                row = session.get(KnowledgeExtractionTaskDocument, task_document_id)
                if row:
                    row.extraction_status = "failed"
                    row.failure_code = "EMPTY_TEXT"
                    row.checkpoint = {
                        "batch": 0,
                        "status": "failed",
                        "failure_code": "EMPTY_TEXT",
                    }
                    if task is not None:
                        self._append_event(
                            session,
                            task,
                            "document.extraction_failed",
                            {
                                "task_document_id": row.id,
                                "processed": ordinal,
                                "total": total,
                                "failure_code": "EMPTY_TEXT",
                            },
                        )
                    session.commit()
            return
        document_requested_fields = requested_fields_for_document(
            task_document.canonical_path,
            requested_fields,
        )
        last_activity_report = 0.0

        async def report_model_activity(activity: dict[str, Any]) -> None:
            nonlocal last_activity_report
            now = time.monotonic()
            if not activity.get("done") and now - last_activity_report < 5:
                return
            last_activity_report = now
            with self._database.session_factory() as session:
                task = session.get(KnowledgeExtractionTask, extraction_id)
                row = session.get(
                    KnowledgeExtractionTaskDocument,
                    task_document_id,
                )
                if task is None or row is None:
                    return
                row.checkpoint = {
                    "batch": 0,
                    "status": "extracting",
                    "model_activity_at": utc_now().isoformat(),
                    "model_chunks_received": activity.get("chunk_index", 0),
                    "model_response_chars": activity.get("response_chars", 0),
                    "model_done": bool(activity.get("done")),
                }
                self._append_event(
                    session,
                    task,
                    "document.model.activity",
                    {
                        "task_document_id": row.id,
                        "processed": ordinal,
                        "total": total,
                        **row.checkpoint,
                    },
                )
                session.commit()

        try:
            if document_requested_fields:
                fields, validation_errors = (
                    await self._knowledge_service.extract_customer_fields(
                        requested_fields=document_requested_fields,
                        results=results,
                        schema_registry=schema_registry,
                        timeout_seconds=(
                            self._settings
                            .knowledge_customer_document_timeout_seconds
                        ),
                        activity=report_model_activity,
                    )
                )
            else:
                fields, validation_errors = [], []
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
            row.failure_code = None
            observation = self._document_observation(
                row.canonical_path,
                results,
            )
            row.checkpoint = {
                "batch": 1,
                "status": "completed",
                "validation_errors": validation_errors,
                **({"observation": observation} if observation else {}),
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
                    **(
                        {"observation_status": observation["status"]}
                        if observation
                        else {}
                    ),
                },
            )
            session.commit()

    @staticmethod
    def _document_observation(
        canonical_path: str,
        results: list[SearchResult],
    ) -> dict[str, Any] | None:
        if not canonical_path.casefold().endswith(".lnk"):
            return None
        values: dict[str, str] = {}
        for result in results:
            for line in result.text.splitlines():
                key, separator, value = line.partition(":")
                if separator and key.startswith("shortcut_"):
                    values[key] = value.strip()
        status = values.get("shortcut_target_status", "shortcut_parse_failed")
        target_path = values.get("shortcut_target_path")
        if target_path:
            target_path = scan_knowledge_text(target_path).safe_text
        return {
            "type": "windows_shortcut",
            "status": status,
            "target_path": target_path,
            "target_kind": values.get("shortcut_target_kind"),
        }

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
            object_list_codes = {
                item["code"]
                for item in task.request_json["requested_fields"]
                if item.get("type") == "object_list"
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
                conflicting_values = (
                    len(best) > 1 and field_code not in object_list_codes
                )
                if conflicting_values:
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
                        "conflict" if conflicting_values else "selected"
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
                "document_exclusions": [
                    {
                        "document_id": item.document_id,
                        "canonical_path": item.canonical_path,
                        "reason_code": item.excluded_reason,
                    }
                    for item in documents
                    if item.extraction_status == "excluded"
                ],
                "document_observations": [
                    {
                        "document_id": item.document_id,
                        "canonical_path": item.canonical_path,
                        **item.checkpoint["observation"],
                    }
                    for item in documents
                    if item.checkpoint.get("observation")
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
        task.updated_at = utc_now()
        if task.scope_id is not None:
            scope = session.get(KnowledgeAnalysisScope, task.scope_id)
            source = (
                session.get(KnowledgeSource, scope.source_id)
                if scope is not None
                else None
            )
            expected_owner = f"extraction:{task.scope_id}:{task.id}"
            if source is not None and source.sync_lease_owner == expected_owner:
                source.sync_lease_expires_at = utc_now() + timedelta(
                    seconds=self._knowledge_service.SOURCE_LEASE_SECONDS
                )
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
        generic = session.get(Task, task.generic_task_id)
        if generic is not None:
            public_type = {
                "scope.resolution.started": "task.started",
                "aggregation.completed": "task.completed",
                "extraction.failed": "task.failed",
            }.get(event_type, "task.progress")
            self._task_service.append_event(
                session,
                task=generic,
                event_type=public_type,
                data={
                    "extraction_task_id": task.id,
                    "extraction_event_type": event_type,
                    "stage": task.stage,
                    **data,
                },
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

    def cancel(self, extraction_id: str, generic_task_id: str) -> None:
        with self._database.session_factory() as session:
            task = session.get(KnowledgeExtractionTask, extraction_id)
            generic = session.get(Task, generic_task_id)
            if task is not None and task.status not in TERMINAL_EXTRACTION_STATUSES:
                task.status = "cancelled"
                task.stage = "cancelled"
                task.completed_at = utc_now()
                task.result_json = {
                    "id": task.id,
                    "schema_version": 1,
                    "status": "cancelled",
                    "subject_external_id": task.subject_external_id,
                    "created_at": task.created_at.isoformat(),
                    "completed_at": task.completed_at.isoformat(),
                }
                self._append_event(
                    session,
                    task,
                    "extraction.cancelled",
                    {},
                )
            if generic is not None and generic.status not in TaskStatus.TERMINAL:
                generic.status = TaskStatus.CANCELLED
                generic.completed_at = utc_now()
            session.commit()
