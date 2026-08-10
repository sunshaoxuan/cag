import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.runtimes.base import RuntimeEventCallback, RuntimeResult
from tests.waiters import wait_for_task


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

    completed = wait_for_task(client, str(created["id"]))
    assert completed["status"] == "completed"
    assert completed["started_at"] is not None
    assert completed["completed_at"] is not None
    assert completed["workspace_id"].endswith(str(created["id"]))
    assert len(completed["workspace_commit"]) == 40
    assert completed["final_report"]["status"] == "completed"
    assert completed["final_report"]["validation"][0]["status"] == "passed"


def test_task_persists_model_routing_context(client: TestClient) -> None:
    routing_context = {
        "routePolicyVersion": "oneops-ai-resilient-routing-v3",
        "taskClass": "TRANSLATION",
        "objectiveSummary": "後続の入力を日本語へ翻訳する",
        "targetLanguage": "ja",
        "constraints": ["原文の構造と書式を維持する"],
        "continuationMode": "INHERITED",
        "taskFingerprint": "a" * 64,
        "attemptNumber": 1,
        "tier": "SIMPLE",
        "modelSettingId": "11111111-1111-4111-8111-111111111111",
        "gatewaySettingId": "22222222-2222-4222-8222-222222222222",
        "model": "gpt-5.6-luna",
        "reasoningEffort": "medium",
        "selectionReason": "LIGHT_TASK_INITIAL_ROUTE",
        "escalationReason": None,
    }
    response = client.post(
        "/api/v1/tasks",
        json={
            "project_id": "test-project",
            "prompt": "Translate this text.",
            "model": "gpt-5.6-luna",
            "effort": "medium",
            "routing_context": routing_context,
        },
    )

    assert response.status_code == 202
    created = response.json()
    assert created["model"] == "gpt-5.6-luna"
    assert created["effort"] == "medium"
    assert created["routing_context"] == routing_context
    audit = client.get(f"/api/v1/audit/tasks/{created['id']}")
    assert audit.status_code == 200
    assert audit.json()["request_metadata"]["routing_context"] == routing_context
    wait_for_task(client, str(created["id"]))
    events = parse_sse(
        client.get(f"/api/v1/tasks/{created['id']}/events").text
    )
    plan = next(event for event in events if event["type"] == "agent.plan")
    assert plan["data"]["model"] == "gpt-5.6-luna"
    assert plan["data"]["reasoning_effort"] == "medium"


def test_task_rejects_inconsistent_model_routing_context(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/tasks",
        json={
            "project_id": "test-project",
            "prompt": "Translate this text.",
            "model": "gpt-5.6-terra",
            "effort": "low",
            "routing_context": {
                "routePolicyVersion": "oneops-ai-task-routing-v1",
                "taskClass": "TRANSLATION",
                "objectiveSummary": "後続の入力を日本語へ翻訳する",
                "targetLanguage": "ja",
                "constraints": [],
                "continuationMode": "NEW_OR_UPDATED",
                "taskFingerprint": "b" * 64,
                "attemptNumber": 1,
                "tier": "SIMPLE",
                "modelSettingId": "11111111-1111-4111-8111-111111111111",
                "gatewaySettingId": "22222222-2222-4222-8222-222222222222",
                "model": "gpt-5.6-luna",
                "reasoningEffort": "low",
                "selectionReason": "LIGHT_TASK_INITIAL_ROUTE",
                "escalationReason": None,
            },
        },
    )

    assert response.status_code == 422


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
    assert [event["sequence"] for event in events] == list(range(1, 12))
    assert [event["type"] for event in events] == [
        "task.created",
        "task.started",
        "workspace.preparing",
        "workspace.ready",
        "agent.plan",
        "agent.message",
        "test.completed",
        "learning.capture.started",
        "learning.signal.recorded",
        "learning.capture.completed",
        "task.completed",
    ]
    assert all(event["task_id"] == task["id"] for event in events)


def test_task_events_can_resume_after_sequence(client: TestClient) -> None:
    task = create_task(client)
    wait_for_task(client, str(task["id"]))

    response = client.get(
        f"/api/v1/tasks/{task['id']}/events",
        params={"after_sequence": 6, "follow": False},
    )

    events = parse_sse(response.text)
    assert [event["sequence"] for event in events] == [7, 8, 9, 10, 11]


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
        persistent_conversation: bool,
        conversation_thread_id: str | None,
        workspace_path: Path,
        additional_workspace_roots: tuple[Path, ...],
        developer_instructions: str | None,
        emit: RuntimeEventCallback,
    ) -> RuntimeResult:
        raise RuntimeError("deterministic runtime failure")


class CapturingRuntime:
    def __init__(self) -> None:
        self.additional_workspace_roots: tuple[Path, ...] = ()
        self.developer_instructions: str | None = None

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
        self.additional_workspace_roots = additional_workspace_roots
        self.developer_instructions = developer_instructions
        return RuntimeResult(
            summary="captured",
            root_cause=None,
            changes=[],
            validation=[],
            approvals=[],
            warnings=[],
            next_actions=[],
        )


def test_runtime_failure_is_persisted(app_factory) -> None:
    with TestClient(app_factory(FailingRuntime())) as client:
        created = create_task(client)
        task = wait_for_task(client, str(created["id"]))
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
        "learning.capture.started",
        "learning.signal.recorded",
        "learning.capture.completed",
        "task.failed",
    ]


def test_disallowed_runtime_profile_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks",
        json={
            "project_id": "test-project",
            "runtime_profile": "unrestricted",
            "prompt": "inspect",
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Runtime profile is not allowed for this project"
    )


def test_gateway_restart_requeues_interrupted_task(app_factory) -> None:
    app = app_factory()
    with TestClient(app) as client:
        task = create_task(client)
        wait_for_task(client, str(task["id"]))
    with app.state.database.session_factory() as session:
        stored = app.state.task_service.get_task(session, task["id"])
        stored.status = "running"
        stored.error = None
        stored.completed_at = None
        session.commit()

    with TestClient(app_factory()) as restarted:
        recovered = wait_for_task(restarted, str(task["id"]))
        events = parse_sse(
            restarted.get(f"/api/v1/tasks/{task['id']}/events").text
        )

    assert recovered["status"] == "completed"
    assert recovered["error"] is None
    assert any(
        event["type"] == "task.requeued"
        and event["data"]["reason"] == "durable_queue_bootstrap"
        for event in events
    )


def test_self_improvement_profile_gets_task_scoped_candidate_root(
    app_factory,
    settings,
    tmp_path: Path,
) -> None:
    runtime = CapturingRuntime()
    settings.self_improvement_root = tmp_path / "codex-selfimp"

    with TestClient(app_factory(runtime)) as client:
        created = client.post(
            "/api/v1/tasks",
            json={
                "project_id": "test-project",
                "runtime_profile": "self-improvement-candidate",
                "prompt": "沉淀可复用流程",
            },
        )
        assert created.status_code == 202
        task = wait_for_task(client, created.json()["id"])

    assert task["status"] == "completed"
    assert len(runtime.additional_workspace_roots) == 1
    candidate_root = runtime.additional_workspace_roots[0]
    assert candidate_root.is_dir()
    assert candidate_root.name == f"cag-{created.json()['id']}"
    assert runtime.developer_instructions is not None
    assert "TASK_LEARNING_RECEIPT.md" in runtime.developer_instructions
    assert "Do not install" in runtime.developer_instructions


def test_each_task_receives_a_distinct_workspace(app_factory) -> None:
    app = app_factory()
    with TestClient(app) as client:
        first = create_task(client)
        second = create_task(client)
        first_task = wait_for_task(client, str(first["id"]))
        second_task = wait_for_task(client, str(second["id"]))

    assert first_task["workspace_id"] != second_task["workspace_id"]
    with app.state.database.session_factory() as session:
        first_model = app.state.task_service.get_task(session, str(first["id"]))
        second_model = app.state.task_service.get_task(session, str(second["id"]))
        assert first_model.workspace_path != second_model.workspace_path
        assert Path(first_model.workspace_path, ".git").is_dir()
        assert Path(second_model.workspace_path, ".git").is_dir()
