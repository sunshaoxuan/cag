from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_app_settings,
    get_database,
    get_session,
    get_task_service,
)
from app.config import Settings
from app.database import Database
from app.events.sse import stream_audit_events
from app.models import Task
from app.services.task_service import TaskNotFoundError, TaskService


router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


class AuditTaskSummary(BaseModel):
    trace_id: str
    task_id: str
    project_id: str
    project_code: str
    conversation_id: str | None
    trigger_source: str
    client_id: str
    client_request_id: str
    request_hash: str
    status: str
    event_count: int
    last_event_type: str | None
    last_global_sequence: int | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    events_url: str
    audit_url: str


class AuditTaskDetail(AuditTaskSummary):
    prompt: str
    runtime_profile: str
    knowledge_mode: str
    harness_profile: str
    learning_mode: str
    request_metadata: dict[str, Any]
    final_report: dict[str, Any] | None
    error: str | None


def summarize_task(
    task_service: TaskService,
    session: Session,
    task: Task,
) -> AuditTaskSummary:
    events = task_service.list_events(session, task_id=task.id)
    last_event = events[-1] if events else None
    return AuditTaskSummary(
        trace_id=task.id,
        task_id=task.id,
        project_id=task.project_id,
        project_code=task.project.code,
        conversation_id=task.conversation_id,
        trigger_source=task.trigger_source,
        client_id=task.client_id,
        client_request_id=task.client_request_id,
        request_hash=task.request_hash,
        status=task.status,
        event_count=len(events),
        last_event_type=last_event.type if last_event is not None else None,
        last_global_sequence=(
            last_event.global_sequence if last_event is not None else None
        ),
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        events_url=f"/api/v1/tasks/{task.id}/events",
        audit_url=f"/api/v1/audit/tasks/{task.id}",
    )


@router.get("/tasks", response_model=list[AuditTaskSummary])
def list_audit_tasks(
    trigger_source: Annotated[
        str | None,
        Query(max_length=32, pattern=r"^[A-Za-z0-9._-]+$"),
    ] = None,
    client_id: Annotated[
        str | None,
        Query(max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
    ] = None,
    status: Annotated[
        str | None,
        Query(
            max_length=32,
            pattern=(
                r"^(queued|preparing|running|waiting_approval|"
                r"completed|failed|cancelled)$"
            ),
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
) -> list[AuditTaskSummary]:
    tasks = task_service.list_audit_tasks(
        session,
        trigger_source=trigger_source,
        client_id=client_id,
        status=status,
        limit=limit,
    )
    return [
        summarize_task(task_service, session, task)
        for task in tasks
    ]


@router.get("/tasks/{task_id}", response_model=AuditTaskDetail)
def get_audit_task(
    task_id: str,
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
) -> AuditTaskDetail:
    try:
        task = task_service.get_task(session, task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    summary = summarize_task(task_service, session, task)
    return AuditTaskDetail(
        **summary.model_dump(),
        prompt=task.prompt,
        runtime_profile=task.runtime_profile,
        knowledge_mode=task.knowledge_mode,
        harness_profile=task.harness_profile,
        learning_mode=task.learning_mode,
        request_metadata=task.request_metadata,
        final_report=task.final_report,
        error=task.error,
    )


@router.get("/events")
def get_audit_events(
    after_sequence: Annotated[int, Query(ge=0)] = 0,
    follow: bool = True,
    trigger_source: Annotated[
        str | None,
        Query(max_length=32, pattern=r"^[A-Za-z0-9._-]+$"),
    ] = None,
    client_id: Annotated[
        str | None,
        Query(max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
    ] = None,
    task_id: Annotated[
        str | None,
        Query(pattern=r"^[0-9a-fA-F-]{36}$"),
    ] = None,
    last_event_id: Annotated[
        str | None,
        Header(alias="Last-Event-ID"),
    ] = None,
    task_service: TaskService = Depends(get_task_service),
    database: Database = Depends(get_database),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    resume_sequence = after_sequence
    if last_event_id is not None:
        try:
            resume_sequence = max(resume_sequence, int(last_event_id))
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail="Last-Event-ID must be an integer",
            ) from exc
    return StreamingResponse(
        stream_audit_events(
            database=database,
            task_service=task_service,
            after_sequence=resume_sequence,
            follow=follow,
            poll_interval_ms=settings.sse_poll_interval_ms,
            trigger_source=trigger_source,
            client_id=client_id,
            task_id=task_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
