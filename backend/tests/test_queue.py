from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.models import (
    KnowledgeIngestion,
    KnowledgeIngestionEvent,
    KnowledgeSource,
    Project,
    QueueItem,
    QueueItemStatus,
    Task,
)
from app.models.base import utc_now
from app.queue.notifier import QueueNotifier
from tests.waiters import wait_for_task


def create_conversation(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/conversations",
        json={"project_id": "test-project", "title": "queue test"},
    )
    assert response.status_code == 201
    return response.json()


def submit_task(
    client: TestClient,
    *,
    conversation_id: str | None = None,
    request_id: str = "queue-test",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/tasks",
        headers={
            "X-CAG-Client-ID": "queue-tests",
            "X-Request-ID": request_id,
        },
        json={
            "project_id": "test-project",
            "conversation_id": conversation_id,
            "prompt": "run through the durable queue",
        },
    )
    assert response.status_code == 202
    return response.json()


def test_task_is_persisted_and_completed_by_queue(app_factory) -> None:
    app = app_factory()
    with TestClient(app) as client:
        task = submit_task(client)
        completed = wait_for_task(client, str(task["id"]))
        status = client.get("/api/v1/queue/status")
        items = client.get(
            "/api/v1/queue/items",
            params={"queue_name": "interactive"},
        )

    assert completed["status"] == "completed"
    assert status.status_code == 200
    assert status.json()["running"] is True
    assert status.json()["configured_workers"]["interactive"] == 1
    assert items.status_code == 200
    queue_item = next(
        item for item in items.json() if item["task_id"] == task["id"]
    )
    assert queue_item["status"] == "completed"
    assert queue_item["attempt_count"] == 1


def test_same_conversation_is_accepted_and_claimed_in_order(
    app_factory,
    settings,
) -> None:
    settings.queue_enabled = False
    app = app_factory()
    with TestClient(app) as client:
        conversation = create_conversation(client)
        first = submit_task(
            client,
            conversation_id=str(conversation["id"]),
            request_id="conversation-first",
        )
        second = submit_task(
            client,
            conversation_id=str(conversation["id"]),
            request_id="conversation-second",
        )

        first_claim = app.state.queue_service.claim_next(
            queue_name="interactive",
            worker_key="test-worker-one",
        )
        blocked_claim = app.state.queue_service.claim_next(
            queue_name="interactive",
            worker_key="test-worker-two",
        )
        assert first_claim is not None
        assert first_claim.task_id == first["id"]
        assert blocked_claim is None

        with app.state.database.session_factory() as session:
            stored = session.get(QueueItem, first_claim.id)
            stored.status = QueueItemStatus.COMPLETED
            stored.lease_owner = None
            stored.lease_expires_at = None
            stored.completed_at = utc_now()
            session.commit()
        second_claim = app.state.queue_service.claim_next(
            queue_name="interactive",
            worker_key="test-worker-two",
        )

    assert second_claim is not None
    assert second_claim.task_id == second["id"]


def test_expired_lease_is_requeued_with_task_state(
    app_factory,
    settings,
) -> None:
    settings.queue_enabled = False
    app = app_factory()
    with TestClient(app) as client:
        task = submit_task(client)
        claimed = app.state.queue_service.claim_next(
            queue_name="interactive",
            worker_key="expired-worker",
        )
        assert claimed is not None
        with app.state.database.session_factory() as session:
            item = session.get(QueueItem, claimed.id)
            item.lease_expires_at = utc_now() - timedelta(seconds=1)
            stored_task = session.get(Task, str(task["id"]))
            stored_task.status = "running"
            session.commit()

        result = app.state.queue_service.bootstrap()
        items = client.get("/api/v1/queue/items").json()
        recovered = client.get(f"/api/v1/tasks/{task['id']}").json()

    assert result["expired_requeued"] == 1
    assert next(item for item in items if item["id"] == claimed.id)[
        "status"
    ] == "queued"
    assert recovered["status"] == "queued"


def test_queued_item_can_be_cancelled(app_factory, settings) -> None:
    settings.queue_enabled = False
    app = app_factory()
    with TestClient(app) as client:
        task = submit_task(client)
        queue_item = next(
            item
            for item in client.get("/api/v1/queue/items").json()
            if item["task_id"] == task["id"]
        )
        response = client.post(
            f"/api/v1/queue/items/{queue_item['id']}/cancel"
        )
        cancelled = client.get(f"/api/v1/tasks/{task['id']}").json()

    assert response.status_code == 202
    assert response.json()["status"] == "cancelled"
    assert cancelled["status"] == "cancelled"


def test_missing_queue_item_cancel_returns_404(app_factory) -> None:
    with TestClient(app_factory()) as client:
        response = client.post(
            "/api/v1/queue/items/00000000-0000-0000-0000-000000000000/cancel"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Queue item not found"


def test_exhausted_attempt_fails_task_and_lookup_helpers(
    app_factory,
    settings,
) -> None:
    settings.queue_enabled = False
    app = app_factory()
    with TestClient(app) as client:
        task = submit_task(client, request_id="attempt-exhausted")
        claimed = app.state.queue_service.claim_next(
            queue_name="interactive",
            worker_key="failing-worker",
        )
        assert claimed is not None
        with app.state.database.session_factory() as session:
            item = session.get(QueueItem, claimed.id)
            item.max_attempts = 1
            session.commit()
        status = app.state.queue_service.abandon(
            item_id=claimed.id,
            worker_key="failing-worker",
            reason="deterministic worker failure",
        )
        stored = client.get(f"/api/v1/tasks/{task['id']}").json()
        by_task = app.state.queue_service.get_item_for_task(str(task["id"]))
        by_ingestion = app.state.queue_service.get_item_for_ingestion(
            "00000000-0000-0000-0000-000000000000"
        )

    assert status == "failed"
    assert stored["status"] == "failed"
    assert stored["error"] == "deterministic worker failure"
    assert by_task is not None
    assert by_task.status == "failed"
    assert by_ingestion is None


def test_bootstrap_recreates_missing_task_queue_item(
    app_factory,
    settings,
) -> None:
    settings.queue_enabled = False
    app = app_factory()
    with TestClient(app) as client:
        task = submit_task(client, request_id="missing-queue-item")
        with app.state.database.session_factory() as session:
            item = session.query(QueueItem).filter_by(
                task_id=task["id"]
            ).one()
            session.delete(item)
            stored = session.get(Task, str(task["id"]))
            stored.status = "running"
            session.commit()

        result = app.state.queue_service.bootstrap()
        rebuilt = app.state.queue_service.get_item_for_task(str(task["id"]))
        events = client.get(
            f"/api/v1/tasks/{task['id']}/events",
            params={"follow": False},
        ).text

    assert result["tasks_enqueued"] == 1
    assert rebuilt is not None
    assert rebuilt.status == "queued"
    assert "task.requeued" in events


@pytest.mark.anyio
async def test_disabled_redis_notifier_uses_local_event_only() -> None:
    notifier = QueueNotifier(
        redis_url="redis://127.0.0.1:6379/0",
        channel_prefix="cag:test",
        enabled=False,
    )
    await notifier.start()
    await notifier.publish("knowledge")
    await notifier.wait("knowledge", timeout=0.1)
    await notifier.stop()

    assert notifier.status()["enabled"] is False
    assert notifier.connected is False
    assert notifier.last_error is None


def test_knowledge_queue_bootstrap_cancel_recover_and_fail(
    app_factory,
    settings,
) -> None:
    settings.queue_enabled = False
    app = app_factory()
    with TestClient(app):
        with app.state.database.session_factory() as session:
            project = app.state.task_service.resolve_project(
                session,
                "test-project",
            )
            source = KnowledgeSource(
                project_id=project.id,
                name="Queue knowledge source",
                source_key="queue-knowledge-source",
                root_path="D:/queue-knowledge",
            )
            session.add(source)
            session.flush()
            ingestion = KnowledgeIngestion(
                source_id=source.id,
                status="running",
            )
            session.add(ingestion)
            session.commit()
            ingestion_id = ingestion.id

        bootstrap = app.state.queue_service.bootstrap()
        item = app.state.queue_service.get_item_for_ingestion(ingestion_id)
        assert item is not None
        assert bootstrap["ingestions_enqueued"] == 1
        assert item.status == "queued"

        cancelled = app.state.queue_service.request_cancel(item.id)
        assert cancelled == "cancelled"
        with app.state.database.session_factory() as session:
            stored_ingestion = session.get(
                KnowledgeIngestion,
                ingestion_id,
            )
            assert stored_ingestion.status == "cancelled"
            stored_ingestion.status = "running"
            session.commit()

        recovered = app.state.queue_service.bootstrap()
        item = app.state.queue_service.get_item_for_ingestion(ingestion_id)
        assert item is not None
        assert recovered["ingestions_enqueued"] == 1
        assert item.status == "queued"

        claimed = app.state.queue_service.claim_next(
            queue_name="knowledge",
            worker_key="knowledge-failure-worker",
        )
        assert claimed is not None
        with app.state.database.session_factory() as session:
            stored_item = session.get(QueueItem, claimed.id)
            stored_item.max_attempts = 1
            session.commit()
        failed = app.state.queue_service.abandon(
            item_id=claimed.id,
            worker_key="knowledge-failure-worker",
            reason="knowledge worker failed",
        )
        filtered = app.state.queue_service.list_items(
            queue_name="knowledge",
            status="failed",
            limit=10,
        )
        with app.state.database.session_factory() as session:
            stored_ingestion = session.get(
                KnowledgeIngestion,
                ingestion_id,
            )
            event_types = list(
                session.scalars(
                    session.query(KnowledgeIngestionEvent.type)
                    .filter_by(ingestion_id=ingestion_id)
                    .statement
                )
            )

    assert failed == "failed"
    assert stored_ingestion.status == "failed"
    assert filtered[0]["ingestion_id"] == ingestion_id
    assert "knowledge.ingestion.requeued" in event_types
    assert "knowledge.ingestion.failed" in event_types


@pytest.mark.anyio
async def test_redis_failure_keeps_local_wake_and_poll_fallback() -> None:
    notifier = QueueNotifier(
        redis_url="redis://127.0.0.1:6399/0",
        channel_prefix="cag:test",
        enabled=True,
    )
    await notifier.start()
    await notifier.publish("interactive")
    await notifier.wait("interactive", timeout=0.1)
    status = notifier.status()
    await notifier.stop()

    assert status["connected"] is False
    assert status["delivery_role"] == "wake_up_only"
    assert status["last_error"] is not None
