from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy import func, insert, select, text

from app.knowledge.extractors import SUPPORTED_EXTENSIONS
from app.knowledge.processing_policy import (
    METADATA_ONLY_EXTENSIONS,
    PROCESSING_POLICY_VERSION,
)
from app.models import (
    KnowledgeBaselineRun,
    KnowledgeConversionManifestItem,
    KnowledgeDocument,
    KnowledgeIngestion,
    KnowledgeSource,
    KnowledgeSourceEntry,
)
from app.models.base import new_id, utc_now


BASELINE_SCHEMA_VERSION = "knowledge-conversion-manifest-v1"

PLANNED_TEXT_EXTENSIONS = {
    "",
    ".0",
    ".bat",
    ".chm",
    ".cnf",
    ".config",
    ".csproj",
    ".ctl",
    ".def",
    ".doc",
    ".eml",
    ".en",
    ".euc-kr",
    ".hlp",
    ".htm",
    ".ja",
    ".jrxml",
    ".jsp",
    ".licenses",
    ".msg",
    ".org",
    ".ovpn",
    ".oxps",
    ".policy",
    ".ppt",
    ".rdp",
    ".resx",
    ".rpt",
    ".rtf",
    ".settings",
    ".utf8",
    ".var",
    ".vbs",
    ".xls",
    ".zh",
    ".zh-cn",
    ".zh_tw",
}
PLANNED_OCR_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
}
NEVER_EXTRACT_EXTENSIONS = {
    ".app",
    ".class",
    ".cpl",
    ".dll",
    ".dylib",
    ".exe",
    ".ko",
    ".lib",
    ".msi",
    ".ocx",
    ".pdb",
    ".so",
}
SENSITIVE_METADATA_EXTENSIONS = {
    ".cer",
    ".crt",
    ".key",
    ".p12",
    ".pem",
    ".pfx",
    ".ppk",
}


@dataclass(frozen=True)
class ConversionDecision:
    lifecycle_status: str
    conversion_action: str
    decision_reason: str
    capability: str


def format_capability(extension: str, processing_mode: str) -> str:
    suffix = extension.lower()
    if processing_mode == "path_only" or suffix == ".lnk":
        return "path_knowledge"
    if suffix in SUPPORTED_EXTENSIONS:
        return "supported_text"
    if suffix in PLANNED_OCR_EXTENSIONS:
        return "planned_ocr"
    if suffix in PLANNED_TEXT_EXTENSIONS:
        return "planned_text"
    if suffix in METADATA_ONLY_EXTENSIONS:
        return "safe_unpack_candidate"
    if suffix in NEVER_EXTRACT_EXTENSIONS:
        return "binary_metadata"
    if suffix in SENSITIVE_METADATA_EXTENSIONS:
        return "sensitive_metadata"
    return "content_probe_required"


def canonical_lifecycle_status(
    entry: KnowledgeSourceEntry,
    *,
    has_document: bool,
    active_ingestion_id: str | None,
) -> str:
    if not entry.present or entry.processing_status == "removed":
        return "removed"
    if entry.processing_status == "indexed" and has_document:
        return "indexed"
    if entry.processing_status in {"rejected", "failed", "extraction_failed"}:
        return "rejected"
    if active_ingestion_id and entry.last_seen_ingestion_id == active_ingestion_id:
        return "processing"
    if entry.processing_mode == "metadata_only" or entry.processing_status == (
        "metadata_only"
    ):
        return "metadata_only"
    if entry.processing_mode == "path_only":
        return "indexed" if has_document else "discovered"
    return "discovered"


def conversion_decision(
    entry: KnowledgeSourceEntry,
    *,
    has_document: bool,
    active_ingestion_id: str | None,
) -> ConversionDecision:
    lifecycle = canonical_lifecycle_status(
        entry,
        has_document=has_document,
        active_ingestion_id=active_ingestion_id,
    )
    capability = format_capability(entry.extension, entry.processing_mode)
    if lifecycle == "removed":
        return ConversionDecision(
            lifecycle, "metadata_only", "historical_removed", capability
        )
    if entry.processing_mode == "path_only":
        return ConversionDecision(
            lifecycle, "path_only", entry.reason_code or "path_semantic", capability
        )
    if lifecycle == "indexed" and has_document:
        return ConversionDecision(
            lifecycle, "backfill_object", "indexed_without_artifact", capability
        )
    if capability == "safe_unpack_candidate":
        return ConversionDecision(
            lifecycle, "safe_unpack", "container_requires_sandbox", capability
        )
    if capability in {"binary_metadata", "sensitive_metadata"}:
        return ConversionDecision(
            lifecycle, "metadata_only", capability, capability
        )
    if capability in {"planned_text", "planned_ocr", "content_probe_required"}:
        return ConversionDecision(
            lifecycle, "reclean", capability, capability
        )
    if lifecycle == "rejected":
        return ConversionDecision(
            lifecycle, "reclean", entry.reason_code or "prior_rejection", capability
        )
    if lifecycle in {"processing", "discovered"}:
        return ConversionDecision(
            lifecycle, "reclean", "content_not_indexed", capability
        )
    return ConversionDecision(
        lifecycle, "metadata_only", entry.reason_code or "policy_metadata", capability
    )


def format_capability_matrix() -> dict[str, Any]:
    categories = {
        "supported_text": sorted(SUPPORTED_EXTENSIONS),
        "planned_text": sorted(PLANNED_TEXT_EXTENSIONS),
        "planned_ocr": sorted(PLANNED_OCR_EXTENSIONS),
        "safe_unpack_candidate": sorted(METADATA_ONLY_EXTENSIONS),
        "binary_metadata": sorted(NEVER_EXTRACT_EXTENSIONS),
        "sensitive_metadata": sorted(SENSITIVE_METADATA_EXTENSIONS),
    }
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "policy_version": PROCESSING_POLICY_VERSION,
        "routing_boundary": "extension-metadata-planning-only",
        "content_detection_phase": "planned-phase-2",
        "categories": categories,
    }


class KnowledgeConversionBaselineService:
    def __init__(self, database) -> None:
        self._database = database

    def create_dry_run(self, source_id: str) -> KnowledgeBaselineRun:
        lifecycle_counts: Counter[str] = Counter()
        action_counts: Counter[str] = Counter()
        format_counts: Counter[str] = Counter()
        digest = hashlib.sha256()
        run_id = new_id()
        created_at = utc_now()
        with self._database.session_factory() as session:
            source = session.get(KnowledgeSource, source_id)
            if source is None:
                raise KeyError(source_id)
            active_ingestion = session.scalar(
                select(KnowledgeIngestion)
                .where(
                    KnowledgeIngestion.source_id == source_id,
                    KnowledgeIngestion.status.in_({"queued", "running"}),
                )
                .order_by(KnowledgeIngestion.created_at.desc())
                .limit(1)
            )
            run = KnowledgeBaselineRun(
                id=run_id,
                source_id=source_id,
                active_ingestion_id=(active_ingestion.id if active_ingestion else None),
                schema_version=BASELINE_SCHEMA_VERSION,
                policy_version=PROCESSING_POLICY_VERSION,
                status="running",
                item_count=0,
                manifest_sha256="0" * 64,
                lifecycle_counts={},
                action_counts={},
                format_counts={},
                created_at=created_at,
            )
            session.add(run)
            session.commit()

        try:
            return self._populate_run(
                run_id,
                source_id=source_id,
                active_ingestion_id=(
                    active_ingestion.id if active_ingestion else None
                ),
                created_at=created_at,
                lifecycle_counts=lifecycle_counts,
                action_counts=action_counts,
                format_counts=format_counts,
                digest=digest,
            )
        except Exception as exc:
            with self._database.session_factory() as session:
                failed = session.get(KnowledgeBaselineRun, run_id)
                if failed is not None:
                    failed.status = "failed"
                    failed.error = (
                        f"{type(exc).__name__}: conversion baseline failed"
                    )
                    failed.item_count = session.scalar(
                        select(
                            func.count(KnowledgeConversionManifestItem.id)
                        ).where(
                            KnowledgeConversionManifestItem.baseline_run_id
                            == run_id
                        )
                    ) or 0
                    failed.completed_at = utc_now()
                    session.commit()
            raise

    def _populate_run(
        self,
        run_id: str,
        *,
        source_id: str,
        active_ingestion_id: str | None,
        created_at,
        lifecycle_counts: Counter[str],
        action_counts: Counter[str],
        format_counts: Counter[str],
        digest,
    ) -> KnowledgeBaselineRun:
        with self._database.session_factory() as session:
            if self._database.backend_name == "postgresql":
                session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                )
            last_path: str | None = None
            last_id: str | None = None
            item_count = 0
            while True:
                query = (
                    select(KnowledgeSourceEntry, KnowledgeDocument.id)
                    .outerjoin(
                        KnowledgeDocument,
                        (KnowledgeDocument.source_entry_id == KnowledgeSourceEntry.id)
                        & (
                            KnowledgeDocument.canonical_path
                            == KnowledgeSourceEntry.relative_path
                        ),
                    )
                    .where(KnowledgeSourceEntry.source_id == source_id)
                )
                if last_path is not None and last_id is not None:
                    query = query.where(
                        (
                            (KnowledgeSourceEntry.relative_path > last_path)
                            | (
                                (KnowledgeSourceEntry.relative_path == last_path)
                                & (KnowledgeSourceEntry.id > last_id)
                            )
                        )
                    )
                rows = session.execute(
                    query
                    .order_by(
                        KnowledgeSourceEntry.relative_path,
                        KnowledgeSourceEntry.id,
                    )
                    .limit(500)
                ).all()
                if not rows:
                    break
                values: list[dict[str, Any]] = []
                for entry, document_id in rows:
                    decision = conversion_decision(
                        entry,
                        has_document=document_id is not None,
                        active_ingestion_id=active_ingestion_id,
                    )
                    snapshot = {
                        "entry_kind": entry.entry_kind,
                        "file_size": entry.file_size,
                        "processing_mode": entry.processing_mode,
                        "processing_status": entry.processing_status,
                        "reason_code": entry.reason_code,
                        "present": entry.present,
                        "raw_content_hash": entry.raw_content_hash,
                        "content_hash": entry.content_hash,
                        "processor_fingerprint": entry.processor_fingerprint,
                        "last_seen_ingestion_id": entry.last_seen_ingestion_id,
                    }
                    canonical = {
                        "source_entry_id": entry.id,
                        "document_id": document_id,
                        "relative_path": entry.relative_path,
                        "extension": entry.extension,
                        "lifecycle_status": decision.lifecycle_status,
                        "conversion_action": decision.conversion_action,
                        "decision_reason": decision.decision_reason,
                        "capability": decision.capability,
                        "source_snapshot": snapshot,
                    }
                    digest.update(
                        json.dumps(
                            canonical,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    )
                    digest.update(b"\n")
                    values.append(
                        {
                            "id": new_id(),
                            "baseline_run_id": run_id,
                            "created_at": created_at,
                            **canonical,
                        }
                    )
                    lifecycle_counts[decision.lifecycle_status] += 1
                    action_counts[decision.conversion_action] += 1
                    format_counts[decision.capability] += 1
                    item_count += 1
                session.execute(
                    insert(KnowledgeConversionManifestItem), values
                )
                last_path = rows[-1][0].relative_path
                last_id = rows[-1][0].id
            run = session.get(KnowledgeBaselineRun, run_id)
            if run is None:
                raise RuntimeError("Baseline run disappeared")
            run.status = "completed"
            run.item_count = item_count
            run.manifest_sha256 = digest.hexdigest()
            run.lifecycle_counts = dict(sorted(lifecycle_counts.items()))
            run.action_counts = dict(sorted(action_counts.items()))
            run.format_counts = dict(sorted(format_counts.items()))
            run.completed_at = utc_now()
            session.commit()
            session.refresh(run)
            return run

    def get_run(self, run_id: str) -> KnowledgeBaselineRun:
        with self._database.session_factory() as session:
            run = session.get(KnowledgeBaselineRun, run_id)
            if run is None:
                raise KeyError(run_id)
            session.expunge(run)
            return run

    def list_items(
        self,
        run_id: str,
        *,
        limit: int,
        offset: int,
        lifecycle_status: str | None = None,
        conversion_action: str | None = None,
    ) -> tuple[list[KnowledgeConversionManifestItem], int]:
        with self._database.session_factory() as session:
            if session.get(KnowledgeBaselineRun, run_id) is None:
                raise KeyError(run_id)
            filters = [
                KnowledgeConversionManifestItem.baseline_run_id == run_id
            ]
            if lifecycle_status:
                filters.append(
                    KnowledgeConversionManifestItem.lifecycle_status
                    == lifecycle_status
                )
            if conversion_action:
                filters.append(
                    KnowledgeConversionManifestItem.conversion_action
                    == conversion_action
                )
            total = session.scalar(
                select(func.count(KnowledgeConversionManifestItem.id)).where(
                    *filters
                )
            ) or 0
            items = list(
                session.scalars(
                    select(KnowledgeConversionManifestItem)
                    .where(*filters)
                    .order_by(
                        KnowledgeConversionManifestItem.relative_path,
                        KnowledgeConversionManifestItem.id,
                    )
                    .offset(offset)
                    .limit(limit)
                )
            )
            for item in items:
                session.expunge(item)
            return items, total
