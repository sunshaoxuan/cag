import json

from fastapi.testclient import TestClient
from tests.waiters import wait_for_task


def parse_sse(response_text: str) -> list[dict[str, object]]:
    return [
        json.loads(line.removeprefix("data: "))
        for line in response_text.splitlines()
        if line.startswith("data: ")
    ]


def submit_external_task(
    client: TestClient,
    *,
    prompt: str = "检查外部 API 审计链路",
    source: str = "external_api",
    client_id: str = "erp-integration",
    request_id: str = "erp-request-001",
    idempotency_key: str | None = None,
):
    headers = {
        "X-CAG-Source": source,
        "X-CAG-Client-ID": client_id,
        "X-Request-ID": request_id,
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "project_id": "test-project",
            "prompt": prompt,
            "knowledge_mode": "assist",
            "harness_profile": "single",
            "learning_mode": "capture",
        },
    )


def test_external_submission_returns_trace_and_audit_links(
    client: TestClient,
) -> None:
    response = submit_external_task(client)

    assert response.status_code == 202
    task = response.json()
    wait_for_task(client, task["id"])
    assert task["trace_id"] == task["id"]
    assert task["trigger_source"] == "external_api"
    assert task["client_id"] == "erp-integration"
    assert task["client_request_id"] == "erp-request-001"
    assert len(task["request_hash"]) == 64
    assert task["events_url"] == f"/api/v1/tasks/{task['id']}/events"
    assert task["audit_url"] == f"/api/v1/audit/tasks/{task['id']}"
    assert response.headers["x-cag-trace-id"] == task["id"]
    assert response.headers["x-cag-idempotent-replay"] == "false"
    assert response.headers["location"] == task["audit_url"]

    audit = client.get(task["audit_url"])
    assert audit.status_code == 200
    payload = audit.json()
    assert payload["trace_id"] == task["id"]
    assert payload["event_count"] == 11
    assert payload["last_event_type"] == "task.completed"
    assert payload["request_metadata"]["method"] == "POST"
    assert payload["request_metadata"]["path"] == "/api/v1/tasks"


def test_idempotency_key_replays_the_same_trace_without_reexecution(
    client: TestClient,
) -> None:
    first = submit_external_task(
        client,
        idempotency_key="erp-order-1001",
    )
    replay = submit_external_task(
        client,
        request_id="erp-request-002",
        idempotency_key="erp-order-1001",
    )

    assert replay.status_code == 202
    assert replay.json()["id"] == first.json()["id"]
    assert replay.headers["x-cag-idempotent-replay"] == "true"
    tasks = client.get(
        "/api/v1/audit/tasks",
        params={"client_id": "erp-integration"},
    ).json()
    assert [task["task_id"] for task in tasks] == [first.json()["id"]]

    conflict = submit_external_task(
        client,
        prompt="另一个请求正文",
        idempotency_key="erp-order-1001",
    )
    assert conflict.status_code == 409
    assert (
        conflict.json()["detail"]
        == "Idempotency key already belongs to a different request"
    )


def test_global_audit_sse_tracks_every_task_action_in_one_sequence(
    client: TestClient,
) -> None:
    external = submit_external_task(client)
    console = submit_external_task(
        client,
        prompt="网页测试台调用",
        source="test_console",
        client_id="cag-web-test",
        request_id="web-request-001",
    )
    wait_for_task(client, external.json()["id"])
    wait_for_task(client, console.json()["id"])

    response = client.get(
        "/api/v1/audit/events",
        params={"follow": False},
    )
    events = parse_sse(response.text)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [event["sequence"] for event in events] == list(range(1, 23))
    assert {event["trace_id"] for event in events} == {
        external.json()["id"],
        console.json()["id"],
    }
    assert all(event["type"] for event in events)
    assert events[0]["type"] == "task.created"
    assert events[-1]["type"] == "task.completed"

    console_events = parse_sse(
        client.get(
            "/api/v1/audit/events",
            params={
                "follow": False,
                "trigger_source": "test_console",
            },
        ).text
    )
    assert len(console_events) == 11
    assert all(
        event["trigger_source"] == "test_console"
        for event in console_events
    )


def test_global_audit_sse_resumes_from_last_event_id(
    client: TestClient,
) -> None:
    submitted = submit_external_task(client)
    wait_for_task(client, submitted.json()["id"])

    response = client.get(
        "/api/v1/audit/events",
        headers={"Last-Event-ID": "6"},
        params={"follow": False},
    )
    events = parse_sse(response.text)

    assert [event["sequence"] for event in events] == [7, 8, 9, 10, 11]
