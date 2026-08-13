from typing import Any

import asyncio
import csv
import io
import json
from collections.abc import AsyncIterator, Iterator

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy import and_, func, or_, select
from pydantic import BaseModel, Field, SecretStr, model_validator
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_app_settings,
    get_artifact_evidence_service,
    get_database,
    get_knowledge_service,
    get_queue_coordinator,
    get_session,
    get_task_service,
    require_operations_admin,
)
from app.config import Settings
from app.database import Database
from app.knowledge.service import (
    KnowledgeService,
    KnowledgeUnavailableError,
    summarize_knowledge_error,
)
from app.knowledge.conversion_baseline import (
    KnowledgeConversionBaselineService,
    format_capability_matrix,
)
from app.knowledge.artifact_store import ArtifactUnavailableError
from app.knowledge.artifacts import ArtifactEvidenceService
from app.queue.coordinator import QueueCoordinator
from app.models import (
    KnowledgeIngestion,
    KnowledgeIngestionEvent,
    KnowledgeIngestionRejection,
    KnowledgeChunk,
    KnowledgeBaselineRun,
    KnowledgeConversionManifestItem,
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceEntry,
    KnowledgeStatus,
    ProductVersion,
    Project,
)
from app.services.task_service import ProjectNotFoundError, TaskService


router = APIRouter(prefix="/api/v1", tags=["knowledge"])


class SourceCreate(BaseModel):
    project_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    source_type: str = Field(
        default="local_directory",
        pattern=r"^(local_directory|network_share|git|gitlab|svn)$",
    )
    location: str | None = Field(default=None, min_length=1, max_length=4096)
    root_path: str | None = Field(default=None, min_length=1, max_length=4096)
    reference: str | None = Field(default=None, max_length=255)
    subpath: str | None = Field(default=None, max_length=2048)
    scope: str = Field(default="tenant", pattern=r"^(tenant|product)$")
    approved_for_codex: bool = False
    sync_mode: str = Field(
        default="manual", pattern=r"^(manual|scheduled)$"
    )
    sync_interval_minutes: int = Field(default=60, ge=1, le=10_080)
    credential_username: str | None = Field(default=None, max_length=255)
    credential_secret: SecretStr | None = None

    @model_validator(mode="after")
    def require_location(self) -> "SourceCreate":
        if self.location is None and self.root_path is None:
            raise ValueError("location is required")
        return self


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    source_type: str | None = Field(
        default=None,
        pattern=r"^(local_directory|network_share|git|gitlab|svn)$",
    )
    location: str | None = Field(default=None, min_length=1, max_length=4096)
    reference: str | None = Field(default=None, max_length=255)
    subpath: str | None = Field(default=None, max_length=2048)
    scope: str | None = Field(
        default=None, pattern=r"^(tenant|product)$"
    )
    enabled: bool | None = None
    approved_for_codex: bool | None = None
    sync_mode: str | None = Field(
        default=None, pattern=r"^(manual|scheduled)$"
    )
    sync_interval_minutes: int | None = Field(
        default=None, ge=1, le=10_080
    )
    credential_username: str | None = Field(default=None, max_length=255)
    credential_secret: SecretStr | None = None
    clear_credential: bool = False


class SearchRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=1, max_length=20_000)
    limit: int = Field(default=8, ge=1, le=50)
    profile: str = Field(
        default="balanced",
        pattern=r"^(fast|balanced|deep)$",
    )


class ArtifactPutRequest(BaseModel):
    content: str = Field(max_length=20_000_000)
    media_type: str = Field(default="text/plain", min_length=1, max_length=255)
    artifact_kind: str = Field(
        default="cleaned", pattern=r"^(raw|cleaned|ocr_page|table|manifest)$"
    )
    source_entry_id: str | None = None
    relative_path_snapshot: str | None = Field(default=None, max_length=4096)


def baseline_run_response(item: KnowledgeBaselineRun) -> dict[str, Any]:
    return {
        "id": item.id,
        "source_id": item.source_id,
        "active_ingestion_id": item.active_ingestion_id,
        "schema_version": item.schema_version,
        "policy_version": item.policy_version,
        "status": item.status,
        "error": item.error,
        "item_count": item.item_count,
        "manifest_sha256": item.manifest_sha256,
        "lifecycle_counts": item.lifecycle_counts,
        "action_counts": item.action_counts,
        "format_counts": item.format_counts,
        "created_at": item.created_at,
        "completed_at": item.completed_at,
    }


def conversion_manifest_item_response(
    item: KnowledgeConversionManifestItem,
) -> dict[str, Any]:
    return {
        "id": item.id,
        "baseline_run_id": item.baseline_run_id,
        "source_entry_id": item.source_entry_id,
        "document_id": item.document_id,
        "relative_path": item.relative_path,
        "extension": item.extension,
        "lifecycle_status": item.lifecycle_status,
        "conversion_action": item.conversion_action,
        "decision_reason": item.decision_reason,
        "capability": item.capability,
        "source_snapshot": item.source_snapshot,
        "created_at": item.created_at,
    }


@router.get("/knowledge/conversion/format-capabilities")
def get_format_capabilities() -> dict[str, Any]:
    return format_capability_matrix()


@router.get("/knowledge/artifacts/summary")
def get_artifact_summary(
    service: ArtifactEvidenceService = Depends(get_artifact_evidence_service),
) -> dict[str, int]:
    return service.summary()


@router.put("/knowledge/artifacts")
def put_artifact(
    request: ArtifactPutRequest,
    _: str = Depends(require_operations_admin),
    service: ArtifactEvidenceService = Depends(get_artifact_evidence_service),
) -> dict[str, Any]:
    try:
        artifact = service.put(
            content=request.content.encode("utf-8"),
            media_type=request.media_type,
            artifact_kind=request.artifact_kind,
            source_entry_id=request.source_entry_id,
            relative_path_snapshot=request.relative_path_snapshot,
        )
    except ArtifactUnavailableError as exc:
        raise HTTPException(status_code=503, detail="artifact_unavailable") from exc
    return service.detail(artifact.sha256)


@router.get("/knowledge/artifacts/{checksum}")
def get_artifact(
    checksum: str,
    _: str = Depends(require_operations_admin),
    service: ArtifactEvidenceService = Depends(get_artifact_evidence_service),
) -> dict[str, object]:
    try:
        return service.detail(checksum)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Artifact not found") from exc


@router.get("/knowledge/artifacts/{checksum}/content")
def get_artifact_content(
    checksum: str,
    _: str = Depends(require_operations_admin),
    service: ArtifactEvidenceService = Depends(get_artifact_evidence_service),
) -> FastAPIResponse:
    try:
        artifact, content = service.get(checksum)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Artifact not found") from exc
    except ArtifactUnavailableError as exc:
        raise HTTPException(status_code=503, detail="artifact_unavailable") from exc
    return FastAPIResponse(
        content=content,
        media_type=artifact.media_type,
        headers={
            "ETag": f'"sha256:{artifact.sha256}"',
            "Cache-Control": "private, immutable",
            "X-Content-SHA256": artifact.sha256,
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/knowledge/artifacts/reconciliation-runs")
def reconcile_artifacts(
    repair: bool = Query(default=True),
    _: str = Depends(require_operations_admin),
    service: ArtifactEvidenceService = Depends(get_artifact_evidence_service),
) -> dict[str, Any]:
    try:
        run = service.reconcile(repair=repair)
    except ArtifactUnavailableError as exc:
        raise HTTPException(status_code=503, detail="artifact_unavailable") from exc
    return {
        "id": run.id,
        "status": run.status,
        "checked_artifacts": run.checked_artifacts,
        "checked_replicas": run.checked_replicas,
        "repaired_replicas": run.repaired_replicas,
        "missing_replicas": run.missing_replicas,
        "corrupt_replicas": run.corrupt_replicas,
        "orphan_objects": run.orphan_objects,
        "error": run.error,
        "created_at": run.created_at,
        "completed_at": run.completed_at,
    }


@router.post("/knowledge/sources/{source_id}/conversion-baselines")
def create_conversion_baseline(
    source_id: str,
    database: Database = Depends(get_database),
) -> dict[str, Any]:
    service = KnowledgeConversionBaselineService(database)
    try:
        return baseline_run_response(service.create_dry_run(source_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source not found") from exc


@router.get("/knowledge/conversion-baselines/{run_id}")
def get_conversion_baseline(
    run_id: str,
    database: Database = Depends(get_database),
) -> dict[str, Any]:
    service = KnowledgeConversionBaselineService(database)
    try:
        return baseline_run_response(service.get_run(run_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail="Conversion baseline not found"
        ) from exc


@router.get("/knowledge/conversion-baselines/{run_id}/items")
def list_conversion_manifest_items(
    run_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    lifecycle_status: str | None = Query(
        default=None,
        pattern=r"^(discovered|processing|indexed|metadata_only|rejected|removed)$",
    ),
    conversion_action: str | None = Query(
        default=None,
        pattern=r"^(reuse|backfill_object|reclean|reindex|path_only|safe_unpack|metadata_only|blocked)$",
    ),
    database: Database = Depends(get_database),
) -> dict[str, Any]:
    service = KnowledgeConversionBaselineService(database)
    try:
        items, total = service.list_items(
            run_id,
            limit=limit,
            offset=offset,
            lifecycle_status=lifecycle_status,
            conversion_action=conversion_action,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail="Conversion baseline not found"
        ) from exc
    return {
        "items": [conversion_manifest_item_response(item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def source_response(
    source: KnowledgeSource,
    latest_ingestion: KnowledgeIngestion | None = None,
    entry_summary: dict[str, int] | None = None,
    retrieval_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": source.id,
        "project_id": source.project_id,
        "tenant_id": source.tenant_id,
        "product_version_id": source.product_version_id,
        "active_generation_id": (
            retrieval_health.get("active_generation_id")
            if retrieval_health is not None
            else None
        ),
        "name": source.name,
        "source_type": source.source_type,
        "location": source.root_path,
        "root_path": source.root_path,
        "reference": source.reference,
        "subpath": source.subpath,
        "credential_username": source.credential_username,
        "credential_configured": source.credential_ref is not None,
        "enabled": source.enabled,
        "scope": source.scope,
        "status": source.status,
        "source_commit": source.source_commit,
        "index_fingerprint": source.index_fingerprint,
        "approved_for_codex": source.approved_for_codex,
        "error": source.error,
        "last_validated_at": source.last_validated_at,
        "last_collected_at": source.last_collected_at,
        "sync_mode": source.sync_mode,
        "sync_interval_minutes": source.sync_interval_minutes,
        "next_sync_at": source.next_sync_at,
        "last_sync_attempt_at": source.last_sync_attempt_at,
        "last_content_change_at": source.last_content_change_at,
        "consecutive_failures": source.consecutive_failures,
        "scheduler_claimed": source.sync_lease_expires_at is not None,
        "entry_summary": entry_summary
        or {
            "total": 0,
            "code": 0,
            "document": 0,
            "metadata_only": 0,
            "path_only": 0,
            "removed": 0,
        },
        "retrieval_health": retrieval_health
        or {
            "status": "empty",
            "total_chunks": 0,
            "accessible_chunks": 0,
            "legacy_documents": 0,
            "active_generation_id": None,
        },
        "last_ingestion": (
            ingestion_response(latest_ingestion)
            if latest_ingestion is not None
            else None
        ),
        "created_at": source.created_at,
        "updated_at": source.updated_at,
    }


def ingestion_response(ingestion: KnowledgeIngestion) -> dict[str, Any]:
    return {
        "id": ingestion.id,
        "source_id": ingestion.source_id,
        "status": ingestion.status,
        "files_seen": ingestion.files_seen,
        "chunks_written": ingestion.chunks_written,
        "rejected_files": ingestion.rejected_files,
        "skipped_files": ingestion.skipped_files,
        "unchanged_files": ingestion.unchanged_files,
        "vectors_reused": ingestion.vectors_reused,
        "duplicate_files": ingestion.duplicate_files,
        "changed_files": ingestion.changed_files,
        "removed_files": ingestion.removed_files,
        "trigger": ingestion.trigger,
        "error": ingestion.error,
        "error_summary": (
            summarize_knowledge_error(ingestion.error)
            if ingestion.error
            else None
        ),
        "created_at": ingestion.created_at,
        "started_at": ingestion.started_at,
        "completed_at": ingestion.completed_at,
        "rejection_archive_name": ingestion.rejection_archive_name,
        "rejection_archive_sha256": ingestion.rejection_archive_sha256,
        "rejection_archive_created_at": (
            ingestion.rejection_archive_created_at
        ),
    }


@router.get("/knowledge/status")
async def knowledge_status(
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    return await service.status()


@router.post("/knowledge/sources", status_code=status.HTTP_201_CREATED)
def create_source(
    request: SourceCreate,
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    try:
        project = task_service.resolve_project(session, request.project_id)
        session.commit()
        source = service.create_source(
            project=project,
            name=request.name,
            source_type=request.source_type,
            location=request.location or request.root_path or "",
            reference=request.reference,
            subpath=request.subpath,
            scope=request.scope,
            approved_for_codex=request.approved_for_codex,
            sync_mode=request.sync_mode,
            sync_interval_minutes=request.sync_interval_minutes,
            credential_username=request.credential_username,
            credential_secret=(
                request.credential_secret.get_secret_value()
                if request.credential_secret is not None
                else None
            ),
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return source_response(source)


@router.get("/knowledge/sources")
def list_sources(
    session: Session = Depends(get_session),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> list[dict[str, Any]]:
    responses = []
    for item in service.list_sources():
        latest = session.scalar(
            select(KnowledgeIngestion)
            .where(KnowledgeIngestion.source_id == item.id)
            .order_by(KnowledgeIngestion.created_at.desc())
        )
        responses.append(
            source_response(
                item,
                latest,
                source_entry_summary(session, item.id),
                source_retrieval_health(session, item, latest),
            )
        )
    return responses


def source_retrieval_health(
    session: Session,
    source: KnowledgeSource,
    latest_ingestion: KnowledgeIngestion | None,
) -> dict[str, Any]:
    total_chunks = int(
        session.scalar(
            select(func.count(KnowledgeChunk.id))
            .join(KnowledgeDocument)
            .where(KnowledgeDocument.source_id == source.id)
        )
        or 0
    )
    legacy_documents = int(
        session.scalar(
            select(func.count(KnowledgeDocument.id)).where(
                KnowledgeDocument.source_id == source.id,
                or_(
                    KnowledgeDocument.processing_mode == "legacy",
                    KnowledgeDocument.processor_fingerprint.is_(None),
                ),
            )
        )
        or 0
    )
    active_generation_id = session.scalar(
        select(KnowledgeIngestion.id)
        .where(
            KnowledgeIngestion.source_id == source.id,
            KnowledgeIngestion.status == "completed",
        )
        .order_by(
            KnowledgeIngestion.completed_at.desc(),
            KnowledgeIngestion.created_at.desc(),
        )
        .limit(1)
    )
    project = session.get(Project, source.project_id)
    scope_matches = False
    if project is not None and source.scope == "tenant":
        scope_matches = (
            source.tenant_id is not None
            and source.tenant_id == project.tenant_id
        )
    elif (
        project is not None
        and source.scope == "product"
        and source.product_version_id is not None
        and project.product_version_id is not None
    ):
        source_product_id = session.scalar(
            select(ProductVersion.product_id).where(
                ProductVersion.id == source.product_version_id
            )
        )
        project_product_id = session.scalar(
            select(ProductVersion.product_id).where(
                ProductVersion.id == project.product_version_id
            )
        )
        scope_matches = (
            source_product_id is not None
            and source_product_id == project_product_id
        )
    accessible_chunks = total_chunks if scope_matches else 0
    refreshing = (
        latest_ingestion is not None
        and latest_ingestion.status in {"queued", "running"}
    )
    stale_refresh = (
        source.consecutive_failures > 0
        or (
            source.last_sync_attempt_at is not None
            and (
                source.last_collected_at is None
                or source.last_sync_attempt_at > source.last_collected_at
            )
            and not refreshing
        )
    )
    if not source.enabled:
        health_status = "disabled"
    elif accessible_chunks > 0 and (source.error or stale_refresh):
        health_status = "degraded"
    elif accessible_chunks > 0 and refreshing:
        health_status = "refreshing"
    elif (
        accessible_chunks > 0
        and source.approved_for_codex
        and source.status in {
            KnowledgeStatus.APPROVED,
            KnowledgeStatus.INDEXING,
            KnowledgeStatus.FAILED,
        }
    ):
        health_status = "searchable"
    elif total_chunks > 0 and not scope_matches:
        health_status = "scope_mismatch"
    elif total_chunks > 0 and not source.approved_for_codex:
        health_status = "approval_required"
    elif refreshing:
        health_status = "indexing"
    else:
        health_status = "empty"
    return {
        "status": health_status,
        "freshness_status": (
            "refreshing"
            if refreshing
            else "stale"
            if stale_refresh
            else "current"
            if source.last_collected_at is not None
            else "never_collected"
        ),
        "total_chunks": total_chunks,
        "accessible_chunks": accessible_chunks,
        "legacy_documents": legacy_documents,
        "active_generation_id": active_generation_id,
        "last_collected_at": source.last_collected_at,
        "last_sync_attempt_at": source.last_sync_attempt_at,
        "consecutive_failures": source.consecutive_failures,
    }


def source_entry_summary(
    session: Session,
    source_id: str,
) -> dict[str, int]:
    summary = {
        "total": 0,
        "code": 0,
        "document": 0,
        "metadata_only": 0,
        "path_only": 0,
        "removed": 0,
    }
    rows = session.execute(
        select(
            KnowledgeSourceEntry.processing_mode,
            KnowledgeSourceEntry.present,
            func.count(KnowledgeSourceEntry.id),
        )
        .where(KnowledgeSourceEntry.source_id == source_id)
        .group_by(
            KnowledgeSourceEntry.processing_mode,
            KnowledgeSourceEntry.present,
        )
    )
    for mode, present, count in rows:
        summary["total"] += count
        if present and mode in summary:
            summary[mode] += count
        if not present:
            summary["removed"] += count
    return summary


@router.patch("/knowledge/sources/{source_id}")
def update_source(
    source_id: str,
    request: SourceUpdate,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    try:
        source = service.update_source(
            source_id,
            name=request.name,
            source_type=request.source_type,
            location=request.location,
            reference=request.reference,
            subpath=request.subpath,
            scope=request.scope,
            enabled=request.enabled,
            approved_for_codex=request.approved_for_codex,
            sync_mode=request.sync_mode,
            sync_interval_minutes=request.sync_interval_minutes,
            credential_username=request.credential_username,
            credential_secret=(
                request.credential_secret.get_secret_value()
                if request.credential_secret is not None
                else None
            ),
            clear_credential=request.clear_credential,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return source_response(source)


@router.delete(
    "/knowledge/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_source(
    source_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> None:
    try:
        service.delete_source(source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source not found") from exc


@router.post("/knowledge/sources/{source_id}/credential/reveal")
def reveal_source_credential(
    source_id: str,
    response: Response,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, str]:
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    try:
        credential = service.reveal_source_credential(source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source not found") from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail="Source credential is not configured",
        ) from exc
    return {
        "username": credential.username,
        "secret": credential.secret,
    }


@router.post("/knowledge/sources/{source_id}/validate")
async def validate_source(
    source_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    try:
        result = await service.validate_source(source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "ok": result.ok,
        "revision": result.revision,
        "message": result.message,
    }


@router.post(
    "/knowledge/sources/{source_id}/ingest",
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_source(
    source_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
    queue_coordinator: QueueCoordinator = Depends(get_queue_coordinator),
) -> dict[str, Any]:
    try:
        ingestion, created = service.create_ingestion(source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if created:
        await queue_coordinator.notify("knowledge")
    return ingestion_response(ingestion)


@router.get("/knowledge/sources/{source_id}/ingestions")
def list_source_ingestions(
    source_id: str,
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    if session.get(KnowledgeSource, source_id) is None:
        raise HTTPException(status_code=404, detail="Source not found")
    ingestions = session.scalars(
        select(KnowledgeIngestion)
        .where(KnowledgeIngestion.source_id == source_id)
        .order_by(KnowledgeIngestion.created_at.desc())
        .limit(50)
    )
    return [ingestion_response(item) for item in ingestions]


def source_entry_response(item: KnowledgeSourceEntry) -> dict[str, Any]:
    return {
        "id": item.id,
        "source_id": item.source_id,
        "relative_path": item.relative_path,
        "entry_kind": item.entry_kind,
        "extension": item.extension,
        "file_size": item.file_size,
        "modified_at": item.modified_at,
        "processing_mode": item.processing_mode,
        "processing_status": item.processing_status,
        "reason_code": item.reason_code,
        "extractor": item.extractor,
        "extractor_version": item.extractor_version,
        "retryable": item.retryable,
        "detected_mime": item.detected_mime,
        "detected_magic": item.detected_magic,
        "text_probability": item.text_probability,
        "present": item.present,
        "last_seen_ingestion_id": item.last_seen_ingestion_id,
        "processor_fingerprint": item.processor_fingerprint,
        "content_hash": item.content_hash,
        "raw_content_hash": item.raw_content_hash,
        "first_seen_at": item.first_seen_at,
        "last_seen_at": item.last_seen_at,
        "processed_at": item.processed_at,
        "removed_at": item.removed_at,
    }


@router.get("/knowledge/sources/{source_id}/entries")
def list_source_entries(
    source_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    processing_mode: str | None = Query(
        default=None,
        pattern=r"^(code|document|metadata_only|path_only)$",
    ),
    present: bool | None = Query(default=True),
    query: str | None = Query(default=None, max_length=255),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    if session.get(KnowledgeSource, source_id) is None:
        raise HTTPException(status_code=404, detail="Source not found")
    filters: list[Any] = [
        KnowledgeSourceEntry.source_id == source_id
    ]
    if processing_mode:
        filters.append(
            KnowledgeSourceEntry.processing_mode == processing_mode
        )
    if present is not None:
        filters.append(KnowledgeSourceEntry.present.is_(present))
    if query and query.strip():
        filters.append(
            KnowledgeSourceEntry.relative_path.ilike(
                f"%{query.strip()}%"
            )
        )
    total = session.scalar(
        select(func.count(KnowledgeSourceEntry.id)).where(*filters)
    ) or 0
    items = list(
        session.scalars(
            select(KnowledgeSourceEntry)
            .where(*filters)
            .order_by(
                KnowledgeSourceEntry.relative_path,
                KnowledgeSourceEntry.id,
            )
            .offset(offset)
            .limit(limit)
        )
    )
    return {
        "items": [source_entry_response(item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
        "summary": source_entry_summary(session, source_id),
    }


@router.get("/knowledge/ingestions/{ingestion_id}")
def get_ingestion(
    ingestion_id: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    ingestion = session.get(KnowledgeIngestion, ingestion_id)
    if ingestion is None:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    return ingestion_response(ingestion)


def rejection_response(
    item: KnowledgeIngestionRejection,
) -> dict[str, Any]:
    return {
        "id": item.id,
        "ingestion_id": item.ingestion_id,
        "relative_path": item.relative_path,
        "entry_kind": item.entry_kind,
        "disposition": item.disposition,
        "extension": item.extension,
        "file_size": item.file_size,
        "reason_code": item.reason_code,
        "extractor": item.extractor,
        "extractor_version": item.extractor_version,
        "retryable": item.retryable,
        "detected_mime": item.detected_mime,
        "detected_magic": item.detected_magic,
        "error_type": item.error_type,
        "error_message": item.error_message,
        "created_at": item.created_at,
    }


def rejection_filters(
    ingestion_id: str,
    disposition: str | None,
    reason_code: str | None,
    extension: str | None,
) -> list[Any]:
    filters: list[Any] = [
        KnowledgeIngestionRejection.ingestion_id == ingestion_id
    ]
    if disposition:
        filters.append(
            KnowledgeIngestionRejection.disposition == disposition
        )
    if reason_code:
        filters.append(
            KnowledgeIngestionRejection.reason_code == reason_code
        )
    if extension:
        normalized = extension.lower()
        if not normalized.startswith("."):
            normalized = f".{normalized}"
        filters.append(KnowledgeIngestionRejection.extension == normalized)
    return filters


@router.get("/knowledge/ingestions/{ingestion_id}/rejections")
def list_ingestion_rejections(
    ingestion_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    disposition: str | None = Query(
        default=None, pattern=r"^(rejected|skipped)$"
    ),
    reason_code: str | None = Query(
        default=None, min_length=1, max_length=64
    ),
    extension: str | None = Query(
        default=None, min_length=1, max_length=64
    ),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    ingestion = session.get(KnowledgeIngestion, ingestion_id)
    if ingestion is None:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    filters = rejection_filters(
        ingestion_id, disposition, reason_code, extension
    )
    total = int(
        session.scalar(
            select(func.count(KnowledgeIngestionRejection.id)).where(
                *filters
            )
        )
        or 0
    )
    items = list(
        session.scalars(
            select(KnowledgeIngestionRejection)
            .where(*filters)
            .order_by(
                KnowledgeIngestionRejection.created_at,
                KnowledgeIngestionRejection.id,
            )
            .offset(offset)
            .limit(limit)
        )
    )
    summary_rows = session.execute(
        select(
            KnowledgeIngestionRejection.disposition,
            KnowledgeIngestionRejection.reason_code,
            func.count(KnowledgeIngestionRejection.id),
        )
        .where(
            KnowledgeIngestionRejection.ingestion_id == ingestion_id
        )
        .group_by(
            KnowledgeIngestionRejection.disposition,
            KnowledgeIngestionRejection.reason_code,
        )
        .order_by(
            KnowledgeIngestionRejection.disposition,
            KnowledgeIngestionRejection.reason_code,
        )
    )
    return {
        "items": [rejection_response(item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
        "summary": [
            {
                "disposition": row[0],
                "reason_code": row[1],
                "count": row[2],
            }
            for row in summary_rows
        ],
        "archive_available": bool(ingestion.rejection_archive_name),
    }


@router.get("/knowledge/ingestions/{ingestion_id}/rejections/export")
def export_ingestion_rejections(
    ingestion_id: str,
    disposition: str | None = Query(
        default=None, pattern=r"^(rejected|skipped)$"
    ),
    reason_code: str | None = Query(
        default=None, min_length=1, max_length=64
    ),
    extension: str | None = Query(
        default=None, min_length=1, max_length=64
    ),
    database: Database = Depends(get_database),
) -> StreamingResponse:
    with database.session_factory() as session:
        if session.get(KnowledgeIngestion, ingestion_id) is None:
            raise HTTPException(status_code=404, detail="Ingestion not found")
    filters = rejection_filters(
        ingestion_id, disposition, reason_code, extension
    )

    def rows() -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        def emit(values: list[Any]) -> str:
            buffer.seek(0)
            buffer.truncate(0)
            writer.writerow(values)
            return buffer.getvalue()

        yield "\ufeff"
        yield emit(
            [
                "id",
                "ingestion_id",
                "relative_path",
                "entry_kind",
                "disposition",
                "extension",
                "file_size",
                "reason_code",
                "extractor",
                "extractor_version",
                "retryable",
                "detected_mime",
                "detected_magic",
                "error_type",
                "error_message",
                "created_at",
            ]
        )
        cursor_created_at = None
        cursor_id = None
        batch_size = 500
        while True:
            statement = select(KnowledgeIngestionRejection).where(*filters)
            if cursor_created_at is not None and cursor_id is not None:
                statement = statement.where(
                    or_(
                        KnowledgeIngestionRejection.created_at
                        > cursor_created_at,
                        and_(
                            KnowledgeIngestionRejection.created_at
                            == cursor_created_at,
                            KnowledgeIngestionRejection.id > cursor_id,
                        ),
                    )
                )
            with database.session_factory() as session:
                items = list(
                    session.scalars(
                        statement.order_by(
                            KnowledgeIngestionRejection.created_at,
                            KnowledgeIngestionRejection.id,
                        ).limit(batch_size)
                    )
                )
            if not items:
                return
            cursor_created_at = items[-1].created_at
            cursor_id = items[-1].id
            for item in items:
                yield emit(
                    [
                        item.id,
                        item.ingestion_id,
                        item.relative_path,
                        item.entry_kind,
                        item.disposition,
                        item.extension,
                        item.file_size,
                        item.reason_code,
                        item.extractor,
                        item.extractor_version,
                        item.retryable,
                        item.detected_mime,
                        item.detected_magic,
                        item.error_type,
                        item.error_message,
                        item.created_at.isoformat(),
                    ]
                )
            if len(items) < batch_size:
                return

    return StreamingResponse(
        rows(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="knowledge-rejections-{ingestion_id}.csv"'
            ),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/knowledge/ingestions/{ingestion_id}/rejections/archive")
def download_ingestion_rejection_archive(
    ingestion_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> FileResponse:
    try:
        path = service.rejection_archive_path(ingestion_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail="Ingestion not found"
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="Rejection archive not found"
        ) from exc
    return FileResponse(
        path,
        media_type="application/gzip",
        filename=path.name,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def stream_ingestion_events(
    database: Database,
    ingestion_id: str,
    after_sequence: int,
    follow: bool,
) -> AsyncIterator[str]:
    current = after_sequence
    while True:
        with database.session_factory() as session:
            ingestion = session.get(KnowledgeIngestion, ingestion_id)
            if ingestion is None:
                return
            events = list(
                session.scalars(
                    select(KnowledgeIngestionEvent)
                    .where(
                        KnowledgeIngestionEvent.ingestion_id == ingestion_id,
                        KnowledgeIngestionEvent.sequence > current,
                    )
                    .order_by(KnowledgeIngestionEvent.sequence)
                )
            )
            terminal = ingestion.status in {"completed", "failed", "cancelled"}
        for event in events:
            current = event.sequence
            payload = {
                "event_id": event.id,
                "ingestion_id": ingestion_id,
                "sequence": event.sequence,
                "type": event.type,
                "timestamp": event.created_at.isoformat(),
                "data": event.data,
            }
            yield (
                f"id: {event.sequence}\n"
                f"event: {event.type}\n"
                f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            )
        if not follow or terminal:
            return
        await asyncio.sleep(0.1)


@router.get("/knowledge/ingestions/{ingestion_id}/events")
def get_ingestion_events(
    ingestion_id: str,
    after_sequence: int = Query(default=0, ge=0),
    follow: bool = True,
    database: Database = Depends(get_database),
) -> StreamingResponse:
    with database.session_factory() as session:
        if session.get(KnowledgeIngestion, ingestion_id) is None:
            raise HTTPException(status_code=404, detail="Ingestion not found")
    return StreamingResponse(
        stream_ingestion_events(
            database,
            ingestion_id,
            after_sequence,
            follow,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/knowledge/search")
async def search_knowledge(
    request: SearchRequest,
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    service: KnowledgeService = Depends(get_knowledge_service),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    try:
        project = task_service.resolve_project(session, request.project_id)
        session.commit()
        timeout_seconds = {
            "fast": settings.knowledge_fast_timeout_seconds,
            "balanced": settings.knowledge_balanced_timeout_seconds,
            "deep": settings.knowledge_deep_timeout_seconds,
        }[request.profile]
        def execute_isolated_search():
            return asyncio.run(
                service.search(
                    project=project,
                    query=request.query.strip(),
                    limit=request.limit,
                    profile=request.profile,
                )
            )

        results = await asyncio.wait_for(
            asyncio.to_thread(execute_isolated_search),
            timeout=timeout_seconds,
        )
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=f"Knowledge search exceeded {timeout_seconds} seconds",
        ) from exc
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except KnowledgeUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Knowledge search failed in a bounded retrieval stage",
        ) from exc
    return {
        "query": request.query,
        "results": [
            {
                "chunk_id": item.id,
                "source_entry_id": item.source_entry_id,
                "source_id": item.source_id,
                "source_name": item.source_name,
                "source_type": item.source_type,
                "path": item.path,
                "resource_uri": item.resource_uri,
                "generation_id": item.generation_id,
                "text": item.text,
                "score": item.score,
                "scope": item.scope,
                "source_commit": item.source_commit,
                "match_reasons": item.match_reasons,
                "symbol_ids": item.symbol_ids,
            }
            for item in results
        ],
    }


@router.get("/knowledge/code/summary")
def code_knowledge_summary(
    project_id: str = Query(min_length=1, max_length=128),
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    try:
        project = task_service.resolve_project(session, project_id)
        session.commit()
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    return service.code_summary(project)


@router.get("/knowledge/code/symbols")
def list_code_symbols(
    project_id: str = Query(min_length=1, max_length=128),
    query: str = Query(default="", max_length=2000),
    kind: str = Query(default="", max_length=32),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> list[dict[str, Any]]:
    try:
        project = task_service.resolve_project(session, project_id)
        session.commit()
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    return service.list_code_symbols(
        project=project,
        query=query.strip(),
        kind=kind.strip(),
        limit=limit,
    )


@router.get("/knowledge/code/symbols/{symbol_id}")
def get_code_symbol(
    symbol_id: str,
    project_id: str = Query(min_length=1, max_length=128),
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    try:
        project = task_service.resolve_project(session, project_id)
        session.commit()
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    result = service.code_symbol_detail(
        project=project,
        symbol_id=symbol_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Code symbol not found")
    return result


@router.get("/memory-candidates")
def list_memory_candidates(
    service: KnowledgeService = Depends(get_knowledge_service),
) -> list[dict[str, Any]]:
    return [
        {
            "id": candidate.id,
            "task_id": candidate.task_id,
            "tenant_id": candidate.tenant_id,
            "product_version_id": candidate.product_version_id,
            "scope": candidate.scope,
            "kind": candidate.kind,
            "title": candidate.title,
            "content": content,
            "evidence": candidate.evidence,
            "confidence": candidate.confidence,
            "status": candidate.status,
            "created_at": candidate.created_at,
        }
        for candidate, content in service.list_candidates()
    ]


@router.post("/memory-candidates/{candidate_id}/{action}")
def transition_memory_candidate(
    candidate_id: str,
    action: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    if action not in {"approve", "reject", "promote", "deprecate"}:
        raise HTTPException(status_code=404, detail="Unknown memory action")
    try:
        candidate = service.transition_candidate(candidate_id, action=action)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Candidate not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "id": candidate.id,
        "scope": candidate.scope,
        "status": candidate.status,
    }
