from datetime import datetime

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_app_settings,
    get_database,
    get_session,
    get_task_service,
)
from app.api.tasks import TaskResponse, to_response as task_to_response
from app.config import Settings
from app.database import Database
from app.events.sse import stream_conversation_events
from app.models import Conversation
from app.services.task_service import (
    ConversationNotFoundError,
    ProjectNotFoundError,
    TaskService,
)


router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


class ConversationCreate(BaseModel):
    project_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9._-]+$|^[0-9a-fA-F-]{36}$",
    )
    title: str | None = Field(default=None, max_length=255)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    project_code: str
    title: str | None
    codex_thread_id: str | None
    created_at: datetime


def to_response(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        project_id=conversation.project_id,
        project_code=conversation.project.code,
        title=conversation.title,
        codex_thread_id=conversation.codex_thread_id,
        created_at=conversation.created_at,
    )


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    request: ConversationCreate,
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
) -> ConversationResponse:
    try:
        conversation = task_service.create_conversation(
            session,
            project_reference=request.project_id,
            title=request.title,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    return to_response(conversation)


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str,
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
) -> ConversationResponse:
    try:
        conversation = task_service.get_conversation(session, conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    return to_response(conversation)


@router.get("/{conversation_id}/tasks", response_model=list[TaskResponse])
def list_conversation_tasks(
    conversation_id: str,
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
) -> list[TaskResponse]:
    try:
        tasks = task_service.list_conversation_tasks(
            session,
            conversation_id=conversation_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    return [task_to_response(task) for task in tasks]


@router.get("/{conversation_id}/events")
def get_conversation_events(
    conversation_id: str,
    after_sequence: Annotated[int, Query(ge=0)] = 0,
    follow: bool = True,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    session: Session = Depends(get_session),
    task_service: TaskService = Depends(get_task_service),
    database: Database = Depends(get_database),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    try:
        task_service.get_conversation(session, conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc

    resume_sequence = after_sequence
    if last_event_id is not None and last_event_id.isdigit():
        resume_sequence = max(resume_sequence, int(last_event_id))

    return StreamingResponse(
        stream_conversation_events(
            database=database,
            task_service=task_service,
            conversation_id=conversation_id,
            after_sequence=resume_sequence,
            follow=follow,
            poll_interval_ms=settings.sse_poll_interval_ms,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
