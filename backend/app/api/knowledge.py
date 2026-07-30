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
from sqlalchemy import func, select
from pydantic import BaseModel, Field, SecretStr, model_validator
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_knowledge_service,
    get_queue_coordinator,
    get_session,
    get_task_service,
)
from app.knowledge.service import (
    KnowledgeService,
    KnowledgeUnavailableError,
    summarize_knowledge_error,
)
from app.queue.coordinator import QueueCoordinator
from app.models import (
    KnowledgeIngestion,
    KnowledgeIngestionEvent,
    KnowledgeIngestionRejection,
    KnowledgeSource,
    KnowledgeSourceEntry,
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


def source_response(
    source: KnowledgeSource,
    latest_ingestion: KnowledgeIngestion | None = None,
    entry_summary: dict[str, int] | None = None,
) -> dict[str, Any]:
    return {
        "id": source.id,
        "project_id": source.project_id,
        "tenant_id": source.tenant_id,
        "product_version_id": source.product_version_id,
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
            )
        )
    return responses


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
        "present": item.present,
        "last_seen_ingestion_id": item.last_seen_ingestion_id,
        "processor_fingerprint": item.processor_fingerprint,
        "content_hash": item.content_hash,
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
    session: Session = Depends(get_session),
) -> StreamingResponse:
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
                "error_type",
                "error_message",
                "created_at",
            ]
        )
        result = session.scalars(
            select(KnowledgeIngestionRejection)
            .where(*filters)
            .order_by(
                KnowledgeIngestionRejection.created_at,
                KnowledgeIngestionRejection.id,
            )
            .execution_options(yield_per=500)
        )
        for item in result:
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
                    item.error_type,
                    item.error_message,
                    item.created_at.isoformat(),
                ]
            )

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
    service: KnowledgeService,
    ingestion_id: str,
    after_sequence: int,
    follow: bool,
) -> AsyncIterator[str]:
    current = after_sequence
    while True:
        with service._database.session_factory() as session:
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
    session: Session = Depends(get_session),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> StreamingResponse:
    if session.get(KnowledgeIngestion, ingestion_id) is None:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    return StreamingResponse(
        stream_ingestion_events(service, ingestion_id, after_sequence, follow),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/knowledge/search")
async def search_knowledge(
    request: SearchRequest,
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    try:
        project = task_service.resolve_project(session, request.project_id)
        results = await service.search(
            project=project,
            query=request.query.strip(),
            limit=request.limit,
            profile=request.profile,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except KnowledgeUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "query": request.query,
        "results": [
            {
                "chunk_id": item.id,
                "source_id": item.source_id,
                "source_name": item.source_name,
                "source_type": item.source_type,
                "path": item.path,
                "resource_uri": item.resource_uri,
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
