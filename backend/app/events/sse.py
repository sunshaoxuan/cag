import asyncio
import json
from collections.abc import AsyncIterator
from time import monotonic

from app.database import Database
from app.models import TaskStatus
from app.services.task_service import TaskService


def event_payload(event: object) -> dict[str, object]:
    return {
        "event_id": event.id,
        "task_id": event.task_id,
        "sequence": event.sequence,
        "global_sequence": event.global_sequence,
        "type": event.type,
        "timestamp": event.timestamp.isoformat(),
        "data": event.data,
    }


def format_sse(event: object) -> str:
    data = json.dumps(
        event_payload(event),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"id: {event.sequence}\nevent: {event.type}\ndata: {data}\n\n"


def conversation_event_payload(event: object) -> dict[str, object]:
    return {
        "event_id": event.id,
        "conversation_id": event.conversation_id,
        "task_id": event.task_id,
        "sequence": event.conversation_sequence,
        "task_sequence": event.sequence,
        "global_sequence": event.global_sequence,
        "type": event.type,
        "timestamp": event.timestamp.isoformat(),
        "data": event.data,
    }


def format_conversation_sse(event: object) -> str:
    data = json.dumps(
        conversation_event_payload(event),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        f"id: {event.conversation_sequence}\n"
        f"event: {event.type}\n"
        f"data: {data}\n\n"
    )


def audit_event_payload(event: object) -> dict[str, object]:
    task = event.task
    return {
        "event_id": event.id,
        "trace_id": event.task_id,
        "task_id": event.task_id,
        "sequence": event.global_sequence,
        "task_sequence": event.sequence,
        "conversation_id": event.conversation_id,
        "type": event.type,
        "timestamp": event.timestamp.isoformat(),
        "trigger_source": task.trigger_source,
        "client_id": task.client_id,
        "client_request_id": task.client_request_id,
        "project_id": task.project_id,
        "project_code": task.project.code,
        "data": event.data,
    }


def format_audit_sse(event: object) -> str:
    data = json.dumps(
        audit_event_payload(event),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        f"id: {event.global_sequence}\n"
        "event: audit.event\n"
        f"data: {data}\n\n"
    )


async def stream_task_events(
    *,
    database: Database,
    task_service: TaskService,
    task_id: str,
    after_sequence: int,
    follow: bool,
    poll_interval_ms: int,
) -> AsyncIterator[str]:
    last_sequence = after_sequence

    while True:
        with database.session_factory() as session:
            task = task_service.get_task(session, task_id)
            events = task_service.list_events(
                session,
                task_id=task_id,
                after_sequence=last_sequence,
            )
            status = task.status

        for event in events:
            last_sequence = event.sequence
            yield format_sse(event)

        if not follow or status in TaskStatus.TERMINAL:
            break
        await asyncio.sleep(poll_interval_ms / 1000)


async def stream_conversation_events(
    *,
    database: Database,
    task_service: TaskService,
    conversation_id: str,
    after_sequence: int,
    follow: bool,
    poll_interval_ms: int,
    heartbeat_seconds: int = 15,
) -> AsyncIterator[str]:
    last_sequence = after_sequence
    next_heartbeat = monotonic() + heartbeat_seconds

    while True:
        with database.session_factory() as session:
            events = task_service.list_conversation_events(
                session,
                conversation_id=conversation_id,
                after_sequence=last_sequence,
            )

        for event in events:
            last_sequence = event.conversation_sequence
            yield format_conversation_sse(event)
            next_heartbeat = monotonic() + heartbeat_seconds

        if not follow:
            break
        if monotonic() >= next_heartbeat:
            yield ": keep-alive\n\n"
            next_heartbeat = monotonic() + heartbeat_seconds
        await asyncio.sleep(poll_interval_ms / 1000)


async def stream_audit_events(
    *,
    database: Database,
    task_service: TaskService,
    after_sequence: int,
    follow: bool,
    poll_interval_ms: int,
    trigger_source: str | None = None,
    client_id: str | None = None,
    task_id: str | None = None,
    heartbeat_seconds: int = 15,
) -> AsyncIterator[str]:
    last_sequence = after_sequence
    next_heartbeat = monotonic() + heartbeat_seconds

    while True:
        with database.session_factory() as session:
            events = task_service.list_audit_events(
                session,
                after_sequence=last_sequence,
                trigger_source=trigger_source,
                client_id=client_id,
                task_id=task_id,
            )
            payloads = [
                (event.global_sequence, format_audit_sse(event))
                for event in events
            ]

        for sequence, payload in payloads:
            last_sequence = sequence
            yield payload
            next_heartbeat = monotonic() + heartbeat_seconds

        if not follow:
            break
        if monotonic() >= next_heartbeat:
            yield ": keep-alive\n\n"
            next_heartbeat = monotonic() + heartbeat_seconds
        await asyncio.sleep(poll_interval_ms / 1000)
