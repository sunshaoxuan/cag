from contextlib import contextmanager
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.api.conversations import get_conversation_events
from app.api.tasks import get_task_events


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
    database.dispose()
