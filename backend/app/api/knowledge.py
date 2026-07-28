from typing import Any

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from pydantic import BaseModel, Field, SecretStr, model_validator
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_knowledge_service,
    get_session,
    get_task_service,
)
from app.knowledge.service import KnowledgeService, KnowledgeUnavailableError
from app.models import KnowledgeIngestion, KnowledgeIngestionEvent, KnowledgeSource
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
        "unchanged_files": ingestion.unchanged_files,
        "vectors_reused": ingestion.vectors_reused,
        "duplicate_files": ingestion.duplicate_files,
        "changed_files": ingestion.changed_files,
        "removed_files": ingestion.removed_files,
        "trigger": ingestion.trigger,
        "error": ingestion.error,
        "created_at": ingestion.created_at,
        "started_at": ingestion.started_at,
        "completed_at": ingestion.completed_at,
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
        responses.append(source_response(item, latest))
    return responses


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
def ingest_source(
    source_id: str,
    background_tasks: BackgroundTasks,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> dict[str, Any]:
    try:
        ingestion, created = service.create_ingestion(source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if created:
        background_tasks.add_task(service.ingest, ingestion.id)
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


@router.get("/knowledge/ingestions/{ingestion_id}")
def get_ingestion(
    ingestion_id: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    ingestion = session.get(KnowledgeIngestion, ingestion_id)
    if ingestion is None:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    return ingestion_response(ingestion)


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
                "path": item.path,
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
