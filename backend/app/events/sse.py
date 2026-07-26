import asyncio
import json
from collections.abc import AsyncIterator

from app.database import Database
from app.models import TaskStatus
from app.services.task_service import TaskService


def event_payload(event: object) -> dict[str, object]:
    return {
        "event_id": event.id,
        "task_id": event.task_id,
        "sequence": event.sequence,
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
