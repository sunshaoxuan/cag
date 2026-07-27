from typing import Any

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from pydantic import BaseModel, Field
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
    root_path: str = Field(min_length=1, max_length=4096)
    scope: str = Field(default="tenant", pattern=r"^(tenant|product)$")
    approved_for_codex: bool = False


class SearchRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=1, max_length=20_000)
    limit: int = Field(default=8, ge=1, le=50)


def source_response(source: KnowledgeSource) -> dict[str, Any]:
    return {
        "id": source.id,
        "project_id": source.project_id,
        "tenant_id": source.tenant_id,
        "product_version_id": source.product_version_id,
        "name": source.name,
        "root_path": source.root_path,
        "scope": source.scope,
        "status": source.status,
        "source_commit": source.source_commit,
        "index_fingerprint": source.index_fingerprint,
        "approved_for_codex": source.approved_for_codex,
        "error": source.error,
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
        "error": ingestion.error,
        "created_at": ingestion.created_at,
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
            root_path=request.root_path,
            scope=request.scope,
            approved_for_codex=request.approved_for_codex,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return source_response(source)


@router.get("/knowledge/sources")
def list_sources(
    service: KnowledgeService = Depends(get_knowledge_service),
) -> list[dict[str, Any]]:
    return [source_response(item) for item in service.list_sources()]


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
        ingestion = service.create_ingestion(source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source not found") from exc
    background_tasks.add_task(service.ingest, ingestion.id)
    return ingestion_response(ingestion)


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
            }
            for item in results
        ],
    }


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
