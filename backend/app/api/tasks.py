import hashlib
import json
from datetime import datetime
from typing import Any, Annotated
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_app_settings,
    get_database,
    get_session,
    get_task_executor,
    get_task_service,
)
from app.config import Settings
from app.database import Database
from app.events.sse import stream_task_events
from app.models import Task
from app.services.task_service import (
    ConversationBusyError,
    ConversationNotFoundError,
    ProjectNotFoundError,
    RuntimeProfileNotAllowedError,
    TaskNotFoundError,
    TaskService,
)
from app.tasks.executor import TaskExecutor


router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    project_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9._-]+$|^[0-9a-fA-F-]{36}$",
    )
    prompt: str = Field(min_length=1, max_length=100_000)
    conversation_id: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F-]{36}$",
    )
    runtime_profile: str = Field(
        default="general-engineering",
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    knowledge_mode: str = Field(
        default="assist",
        pattern=r"^(off|assist|required)$",
    )
    harness_profile: str = Field(
        default="single",
        pattern=r"^(single|fast|balanced|deep)$",
    )
    learning_mode: str = Field(
        default="capture",
        pattern=r"^(off|capture|evaluate)$",
    )

    @field_validator("prompt")
    @classmethod
    def prompt_must_contain_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("prompt must contain non-whitespace text")
        return stripped


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trace_id: str
    project_id: str
    project_code: str
    conversation_id: str | None
    trigger_source: str
    client_id: str
    client_request_id: str
    request_hash: str
    events_url: str
    audit_url: str
    prompt: str
    runtime_profile: str
    knowledge_mode: str
    harness_profile: str
    learning_mode: str
    knowledge_usage: dict[str, Any] | None
    status: str
    final_report: dict[str, Any] | None
    error: str | None
    workspace_id: str | None
    workspace_commit: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


def to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        trace_id=task.id,
        project_id=task.project_id,
        project_code=task.project.code,
        conversation_id=task.conversation_id,
        trigger_source=task.trigger_source,
        client_id=task.client_id,
        client_request_id=task.client_request_id,
        request_hash=task.request_hash,
        events_url=f"/api/v1/tasks/{task.id}/events",
        audit_url=f"/api/v1/audit/tasks/{task.id}",
        prompt=task.prompt,
        runtime_profile=task.runtime_profile,
        knowledge_mode=task.knowledge_mode,
        harness_profile=task.harness_profile,
        learning_mode=task.learning_mode,
        knowledge_usage=task.knowledge_usage,
        status=task.status,
        final_report=task.final_report,
        error=task.error,
        workspace_id=task.workspace_id,
        workspace_commit=task.workspace_commit,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_task(
    request: TaskCreate,
    background_tasks: BackgroundTasks,
    http_request: Request,
    http_response: Response,
    trigger_source: Annotated[
        str,
        Header(
            alias="X-CAG-Source",
            min_length=1,
            max_length=32,
            pattern=r"^[A-Za-z0-9._-]+$",
        ),
    ] = "external_api",
    client_id: Annotated[
        str,
        Header(
            alias="X-CAG-Client-ID",
            min_length=1,
            max_length=128,
            pattern=r"^[A-Za-z0-9._-]+$",
        ),
    ] = "anonymous-external",
    client_request_id: Annotated[
        str | None,
        Header(
            alias="X-Request-ID",
            min_length=1,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ] = None,
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=255,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ] = None,
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    task_executor: TaskExecutor = Depends(get_task_executor),
) -> TaskResponse:
    normalized_request = json.dumps(
        request.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    request_hash = hashlib.sha256(normalized_request.encode("utf-8")).hexdigest()
    resolved_request_id = client_request_id or str(uuid4())

    if idempotency_key is not None:
        existing_task = task_service.get_task_by_idempotency(
            session,
            client_id=client_id,
            idempotency_key=idempotency_key,
        )
        if existing_task is not None:
            if existing_task.request_hash != request_hash:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Idempotency key already belongs to a different request"
                    ),
                )
            http_response.headers["X-CAG-Trace-ID"] = existing_task.id
            http_response.headers["X-CAG-Idempotent-Replay"] = "true"
            http_response.headers["Location"] = (
                f"/api/v1/audit/tasks/{existing_task.id}"
            )
            return to_response(existing_task)

    try:
        task = task_service.create_task(
            session,
            project_reference=request.project_id,
            prompt=request.prompt,
            conversation_id=request.conversation_id,
            runtime_profile=request.runtime_profile,
            trigger_source=trigger_source,
            client_id=client_id,
            client_request_id=resolved_request_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            request_metadata={
                "method": http_request.method,
                "path": http_request.url.path,
                "remote_address": (
                    http_request.client.host
                    if http_request.client is not None
                    else None
                ),
                "user_agent": http_request.headers.get(
                    "user-agent",
                    "",
                )[:512],
            },
            knowledge_mode=request.knowledge_mode,
            harness_profile=request.harness_profile,
            learning_mode=request.learning_mode,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except RuntimeProfileNotAllowedError as exc:
        raise HTTPException(
            status_code=422,
            detail="Runtime profile is not allowed for this project",
        ) from exc
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    except ConversationBusyError as exc:
        raise HTTPException(
            status_code=409,
            detail="Conversation already has an active task",
        ) from exc

    response_payload = to_response(task)
    http_response.headers["X-CAG-Trace-ID"] = task.id
    http_response.headers["X-CAG-Idempotent-Replay"] = "false"
    http_response.headers["Location"] = f"/api/v1/audit/tasks/{task.id}"
    background_tasks.add_task(task_executor.execute, task.id)
    return response_payload


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    try:
        task = task_service.get_task(session, task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    return to_response(task)


@router.get("/{task_id}/events")
def get_task_events(
    task_id: str,
    after_sequence: Annotated[int, Query(ge=0)] = 0,
    follow: bool = True,
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    database: Database = Depends(get_database),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    try:
        task_service.get_task(session, task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc

    return StreamingResponse(
        stream_task_events(
            database=database,
            task_service=task_service,
            task_id=task_id,
            after_sequence=after_sequence,
            follow=follow,
            poll_interval_ms=settings.sse_poll_interval_ms,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
