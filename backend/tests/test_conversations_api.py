from pathlib import Path
import json

from fastapi.testclient import TestClient

from app.runtimes.base import RuntimeEventCallback, RuntimeResult


def create_conversation(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/conversations",
        json={
            "project_id": "test-project",
            "title": "持续代理",
        },
    )
    assert response.status_code == 201
    return response.json()


def parse_sse(response_text: str) -> list[dict[str, object]]:
    return [
        json.loads(line.removeprefix("data: "))
        for line in response_text.splitlines()
        if line.startswith("data: ")
    ]


def test_create_and_get_conversation(client: TestClient) -> None:
    created = create_conversation(client)

    assert created["project_code"] == "test-project"
    assert created["project_id"] == "f10d23c0-2d10-4cab-a1fa-f43df90b6c3f"
    assert created["title"] == "持续代理"
    assert created["codex_thread_id"] is None

    response = client.get(f"/api/v1/conversations/{created['id']}")

    assert response.status_code == 200
    fetched = response.json()
    assert fetched["id"] == created["id"]
    assert fetched["project_id"] == created["project_id"]
    assert fetched["project_code"] == created["project_code"]
    assert fetched["title"] == created["title"]
    assert fetched["codex_thread_id"] == created["codex_thread_id"]


def test_conversation_normalizes_blank_title(client: TestClient) -> None:
    response = client.post(
        "/api/v1/conversations",
        json={"project_id": "test-project", "title": "   "},
    )

    assert response.status_code == 201
    assert response.json()["title"] is None


def test_unknown_conversation_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/v1/conversations/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


class PersistentThreadRuntime:
    def __init__(self) -> None:
        self.received_thread_ids: list[str | None] = []

    async def execute(
        self,
        *,
        task_id: str,
        project_code: str,
        prompt: str,
        runtime_profile: str,
        persistent_conversation: bool,
        conversation_thread_id: str | None,
        workspace_path: Path,
        additional_workspace_roots: tuple[Path, ...],
        developer_instructions: str | None,
        emit: RuntimeEventCallback,
    ) -> RuntimeResult:
        self.received_thread_ids.append(conversation_thread_id)
        thread_id = conversation_thread_id or "codex-thread-persisted"
        return RuntimeResult(
            summary=f"completed {prompt}",
            root_cause=None,
            changes=[],
            validation=[],
            approvals=[],
            warnings=[],
            next_actions=[],
            runtime_thread_id=thread_id,
        )


def test_tasks_reuse_persisted_codex_thread(app_factory) -> None:
    runtime = PersistentThreadRuntime()
    with TestClient(app_factory(runtime)) as client:
        conversation = create_conversation(client)
        first = client.post(
            "/api/v1/tasks",
            json={
                "project_id": "test-project",
                "conversation_id": conversation["id"],
                "prompt": "第一轮",
            },
        )
        assert first.status_code == 202
        first_task = client.get(f"/api/v1/tasks/{first.json()['id']}").json()
        assert first_task["status"] == "completed"

        stored = client.get(
            f"/api/v1/conversations/{conversation['id']}"
        ).json()
        assert stored["codex_thread_id"] == "codex-thread-persisted"

        second = client.post(
            "/api/v1/tasks",
            json={
                "project_id": "test-project",
                "conversation_id": conversation["id"],
                "prompt": "第二轮",
            },
        )
        assert second.status_code == 202
        second_task = client.get(f"/api/v1/tasks/{second.json()['id']}").json()
        assert second_task["status"] == "completed"

        tasks = client.get(
            f"/api/v1/conversations/{conversation['id']}/tasks"
        ).json()
        events_response = client.get(
            f"/api/v1/conversations/{conversation['id']}/events",
            params={"follow": "false"},
        )
        events = parse_sse(events_response.text)

    assert runtime.received_thread_ids == [None, "codex-thread-persisted"]
    assert [task["prompt"] for task in tasks] == ["第一轮", "第二轮"]
    assert events_response.status_code == 200
    assert [event["sequence"] for event in events] == list(range(1, 11))
    assert [event["task_sequence"] for event in events] == [
        1,
        2,
        3,
        4,
        5,
        1,
        2,
        3,
        4,
        5,
    ]
    assert all(event["conversation_id"] == conversation["id"] for event in events)


def test_conversation_event_stream_resumes_from_header(app_factory) -> None:
    runtime = PersistentThreadRuntime()
    with TestClient(app_factory(runtime)) as client:
        conversation = create_conversation(client)
        client.post(
            "/api/v1/tasks",
            json={
                "project_id": "test-project",
                "conversation_id": conversation["id"],
                "prompt": "单轮",
            },
        )
        response = client.get(
            f"/api/v1/conversations/{conversation['id']}/events",
            params={"follow": "false"},
            headers={"Last-Event-ID": "3"},
        )

    events = parse_sse(response.text)
    assert [event["sequence"] for event in events] == [4, 5]


def test_conversation_rejects_a_second_active_task(app_factory) -> None:
    app = app_factory()
    with TestClient(app) as client:
        conversation = create_conversation(client)
        with app.state.database.session_factory() as session:
            app.state.task_service.create_task(
                session,
                project_reference="test-project",
                prompt="仍在排队",
                conversation_id=str(conversation["id"]),
                runtime_profile="general-engineering",
            )

        response = client.post(
            "/api/v1/tasks",
            json={
                "project_id": "test-project",
                "conversation_id": conversation["id"],
                "prompt": "并发请求",
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Conversation already has an active task"
