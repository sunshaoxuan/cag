import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.runtimes.base import RuntimeEventCallback, RuntimeResult


def create_task(
    client: TestClient,
    project: str = "test-project",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/tasks",
        json={
            "project_id": project,
            "prompt": "检查构建并运行测试。",
        },
    )
    assert response.status_code == 202
    return response.json()


def parse_sse(response_text: str) -> list[dict[str, object]]:
    return [
        json.loads(line.removeprefix("data: "))
        for line in response_text.splitlines()
        if line.startswith("data: ")
    ]


def test_create_and_get_completed_task(client: TestClient) -> None:
    created = create_task(client)

    assert created["status"] == "queued"
    assert created["project_code"] == "test-project"
    assert created["project_id"] == "f10d23c0-2d10-4cab-a1fa-f43df90b6c3f"
    assert created["final_report"] is None

    response = client.get(f"/api/v1/tasks/{created['id']}")

    assert response.status_code == 200
    completed = response.json()
    assert completed["status"] == "completed"
    assert completed["started_at"] is not None
    assert completed["completed_at"] is not None
    assert completed["workspace_id"].endswith(str(created["id"]))
    assert len(completed["workspace_commit"]) == 40
    assert completed["final_report"]["status"] == "completed"
    assert completed["final_report"]["validation"][0]["status"] == "passed"


def test_project_code_resolves_to_stable_physical_id(client: TestClient) -> None:
    first = create_task(client)
    second = create_task(client)

    assert first["project_id"] == second["project_id"]
    assert first["project_code"] == second["project_code"] == "test-project"


def test_unknown_project_uuid_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks",
        json={
            "project_id": str(uuid4()),
            "prompt": "inspect",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_unknown_conversation_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks",
        json={
            "project_id": "test-project",
            "conversation_id": str(uuid4()),
            "prompt": "inspect",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_prompt_requires_non_whitespace_text(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks",
        json={
            "project_id": "test-project",
            "prompt": "   ",
        },
    )

    assert response.status_code == 422


def test_task_events_are_ordered_sse(client: TestClient) -> None:
    task = create_task(client)

    response = client.get(f"/api/v1/tasks/{task['id']}/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    assert [event["sequence"] for event in events] == list(range(1, 9))
    assert [event["type"] for event in events] == [
        "task.created",
        "task.started",
        "workspace.preparing",
        "workspace.ready",
        "agent.plan",
        "agent.message",
        "test.completed",
        "task.completed",
    ]
    assert all(event["task_id"] == task["id"] for event in events)


def test_task_events_can_resume_after_sequence(client: TestClient) -> None:
    task = create_task(client)

    response = client.get(
        f"/api/v1/tasks/{task['id']}/events",
        params={"after_sequence": 6, "follow": False},
    )

    events = parse_sse(response.text)
    assert [event["sequence"] for event in events] == [7, 8]


def test_missing_task_returns_404(client: TestClient) -> None:
    task_id = str(uuid4())

    assert client.get(f"/api/v1/tasks/{task_id}").status_code == 404
    assert client.get(f"/api/v1/tasks/{task_id}/events").status_code == 404


class FailingRuntime:
    async def execute(
        self,
        *,
        task_id: str,
        project_code: str,
        prompt: str,
        runtime_profile: str,
        workspace_path: Path,
        emit: RuntimeEventCallback,
    ) -> RuntimeResult:
        raise RuntimeError("deterministic runtime failure")


def test_runtime_failure_is_persisted(app_factory) -> None:
    with TestClient(app_factory(FailingRuntime())) as client:
        created = create_task(client)
        task = client.get(f"/api/v1/tasks/{created['id']}").json()
        events = parse_sse(
            client.get(f"/api/v1/tasks/{created['id']}/events").text
        )

    assert task["status"] == "failed"
    assert task["error"] == "deterministic runtime failure"
    assert [event["type"] for event in events] == [
        "task.created",
        "task.started",
        "workspace.preparing",
        "workspace.ready",
        "task.failed",
    ]


def test_each_task_receives_a_distinct_workspace(app_factory) -> None:
    app = app_factory()
    with TestClient(app) as client:
        first = create_task(client)
        second = create_task(client)
        first_task = client.get(f"/api/v1/tasks/{first['id']}").json()
        second_task = client.get(f"/api/v1/tasks/{second['id']}").json()

    assert first_task["workspace_id"] != second_task["workspace_id"]
    with app.state.database.session_factory() as session:
        first_model = app.state.task_service.get_task(session, str(first["id"]))
        second_model = app.state.task_service.get_task(session, str(second["id"]))
        assert first_model.workspace_path != second_model.workspace_path
        assert Path(first_model.workspace_path, ".git").is_dir()
        assert Path(second_model.workspace_path, ".git").is_dir()
