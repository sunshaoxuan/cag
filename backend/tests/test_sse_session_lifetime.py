import asyncio
import csv
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import get_type_hints

from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.api.audit import get_audit_events
from app.api.conversations import get_conversation_events
from app.api.dependencies import get_session
from app.api.knowledge import (
    export_ingestion_rejections,
    get_ingestion_events,
)
from app.api.tasks import get_task_events
from app.models import KnowledgeIngestionRejection


FIXED_REJECTION_CREATED_AT = datetime(2026, 8, 10, tzinfo=UTC)


def tracked_session_factory(database):
    original_factory = database.session_factory
    state = {"active": 0, "closed": 0}

    @contextmanager
    def factory() -> Iterator[Session]:
        state["active"] += 1
        try:
            with original_factory() as session:
                yield session
        finally:
            state["active"] -= 1
            state["closed"] += 1

    return factory, state


async def consume_stream(
    response: StreamingResponse,
    state: dict[str, int],
) -> list[bytes | memoryview | str]:
    chunks: list[bytes | memoryview | str] = []
    async for chunk in response.body_iterator:
        assert state["active"] == 0
        chunks.append(chunk)
    return chunks


def dependency_calls(dependant) -> Iterator[object]:
    for dependency in dependant.dependencies:
        yield dependency.call
        yield from dependency_calls(dependency)


def api_route_contexts(routes) -> Iterator[object]:
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
            continue
        effective_route_contexts = getattr(
            route,
            "effective_route_contexts",
            None,
        )
        if effective_route_contexts is None:
            continue
        for context in effective_route_contexts():
            if isinstance(context.original_route, APIRoute):
                yield context


def create_knowledge_ingestion(
    app,
    source_root: Path,
) -> str:
    database = app.state.database
    database.create_schema()
    with database.session_factory() as session:
        project = app.state.task_service.resolve_project(
            session,
            "test-project",
        )
        session.commit()
    source = app.state.knowledge_service.create_source(
        project=project,
        name="SSE Session Test Source",
        source_type="local_directory",
        location=str(source_root),
        reference=None,
        subpath=None,
        scope="product",
        approved_for_codex=False,
    )
    ingestion, created = app.state.knowledge_service.create_ingestion(
        source.id,
        enqueue=False,
    )
    assert created is True
    with database.session_factory() as session:
        session.add(
            KnowledgeIngestionRejection(
                ingestion_id=ingestion.id,
                relative_path="unsupported.bin",
                disposition="skipped",
                extension=".bin",
                reason_code="unsupported_extension",
                created_at=FIXED_REJECTION_CREATED_AT,
            )
        )
        session.commit()
    return ingestion.id


def test_all_streaming_routes_use_bounded_database_sessions(
    app_factory,
) -> None:
    app = app_factory()
    streaming_routes = [
        route
        for route in api_route_contexts(app.routes)
        if get_type_hints(route.endpoint).get("return") is StreamingResponse
    ]
    assert {route.path for route in streaming_routes} == {
        "/api/v1/audit/events",
        "/api/v1/conversations/{conversation_id}/events",
        "/api/v1/knowledge/ingestions/{ingestion_id}/events",
        (
            "/api/v1/knowledge/ingestions/{ingestion_id}/"
            "rejections/export"
        ),
        "/api/v1/tasks/{task_id}/events",
    }
    assert {
        route.path
        for route in streaming_routes
        if get_session in set(dependency_calls(route.dependant))
    } == set()
    app.state.database.dispose()


def test_conversation_sse_closes_validation_session_before_stream(
    app_factory,
    monkeypatch,
) -> None:
    app = app_factory()
    database = app.state.database
    database.create_schema()
    with database.session_factory() as session:
        conversation = app.state.task_service.create_conversation(
            session,
            project_reference="test-project",
            title="SSE session lifetime",
        )
        conversation_id = conversation.id

    factory, state = tracked_session_factory(database)
    monkeypatch.setattr(database, "session_factory", factory)

    response = get_conversation_events(
        conversation_id,
        after_sequence=0,
        follow=False,
        last_event_id=None,
        task_service=app.state.task_service,
        database=database,
        settings=app.state.settings,
    )

    assert response.media_type == "text/event-stream"
    assert state == {"active": 0, "closed": 1}
    assert asyncio.run(consume_stream(response, state)) == []
    assert state == {"active": 0, "closed": 2}
    database.dispose()


def test_task_sse_closes_validation_session_before_stream(
    app_factory,
    monkeypatch,
) -> None:
    app = app_factory()
    database = app.state.database
    database.create_schema()
    with database.session_factory() as session:
        task = app.state.task_service.create_task(
            session,
            project_reference="test-project",
            prompt="Validate SSE session lifetime.",
            conversation_id=None,
            runtime_profile="general-engineering",
            client_request_id="sse-session-lifetime",
            request_hash="sse-session-lifetime",
        )
        task_id = task.id

    factory, state = tracked_session_factory(database)
    monkeypatch.setattr(database, "session_factory", factory)

    response = get_task_events(
        task_id,
        after_sequence=0,
        follow=False,
        task_service=app.state.task_service,
        database=database,
        settings=app.state.settings,
    )

    assert response.media_type == "text/event-stream"
    assert state == {"active": 0, "closed": 1}
    chunks = asyncio.run(consume_stream(response, state))
    assert chunks
    assert state == {"active": 0, "closed": 2}
    database.dispose()


def test_audit_sse_closes_each_poll_session_before_yield(
    app_factory,
    monkeypatch,
) -> None:
    app = app_factory()
    database = app.state.database
    database.create_schema()
    with database.session_factory() as session:
        app.state.task_service.create_task(
            session,
            project_reference="test-project",
            prompt="Validate audit SSE session lifetime.",
            conversation_id=None,
            runtime_profile="general-engineering",
            client_request_id="audit-sse-session-lifetime",
            request_hash="audit-sse-session-lifetime",
        )

    factory, state = tracked_session_factory(database)
    monkeypatch.setattr(database, "session_factory", factory)

    response = get_audit_events(
        after_sequence=0,
        follow=False,
        trigger_source=None,
        client_id=None,
        task_id=None,
        last_event_id=None,
        task_service=app.state.task_service,
        database=database,
        settings=app.state.settings,
    )

    assert response.media_type == "text/event-stream"
    assert state == {"active": 0, "closed": 0}
    chunks = asyncio.run(consume_stream(response, state))
    assert chunks
    assert state == {"active": 0, "closed": 1}
    database.dispose()


def test_ingestion_sse_closes_validation_and_poll_sessions_before_stream(
    app_factory,
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = app_factory()
    database = app.state.database
    ingestion_id = create_knowledge_ingestion(app, tmp_path)

    factory, state = tracked_session_factory(database)
    monkeypatch.setattr(database, "session_factory", factory)

    response = get_ingestion_events(
        ingestion_id,
        after_sequence=0,
        follow=False,
        database=database,
    )

    assert response.media_type == "text/event-stream"
    assert state == {"active": 0, "closed": 1}
    chunks = asyncio.run(consume_stream(response, state))
    assert chunks
    assert state == {"active": 0, "closed": 2}
    database.dispose()


def test_rejection_export_uses_id_tie_breaker_and_closes_each_batch_session(
    app_factory,
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = app_factory()
    database = app.state.database
    ingestion_id = create_knowledge_ingestion(app, tmp_path)
    with database.session_factory() as session:
        session.add_all(
            [
                KnowledgeIngestionRejection(
                    ingestion_id=ingestion_id,
                    relative_path=f"unsupported-{index:04}.bin",
                    disposition="skipped",
                    extension=".bin",
                    reason_code="unsupported_extension",
                    created_at=FIXED_REJECTION_CREATED_AT,
                )
                for index in range(500)
            ]
        )
        session.commit()

    factory, state = tracked_session_factory(database)
    monkeypatch.setattr(database, "session_factory", factory)

    response = export_ingestion_rejections(
        ingestion_id,
        disposition=None,
        reason_code=None,
        extension=None,
        database=database,
    )

    assert response.media_type == "text/csv; charset=utf-8"
    assert state == {"active": 0, "closed": 1}
    chunks = asyncio.run(consume_stream(response, state))
    content = "".join(
        chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
        for chunk in chunks
    )
    rows = list(csv.DictReader(StringIO(content)))
    assert len(rows) == 501
    assert {row["relative_path"] for row in rows} == {
        "unsupported.bin",
        *(f"unsupported-{index:04}.bin" for index in range(500)),
    }
    assert {row["reason_code"] for row in rows} == {
        "unsupported_extension"
    }
    assert state == {"active": 0, "closed": 3}
    database.dispose()
