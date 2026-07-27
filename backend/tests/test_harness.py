import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import AgentArtifact, AgentRun, ApprovalRequest, HarnessRun, QualityScore
from app.policies.command_policy import CommandPolicyService


def test_command_policy_classifies_safe_approval_and_forbidden() -> None:
    policy = CommandPolicyService()

    assert policy.evaluate("git status", "command").decision == "allow"
    assert policy.evaluate("deploy production", "command").decision == "approval_required"
    forbidden = policy.evaluate("git reset --hard HEAD", "command")
    assert forbidden.decision == "deny"
    assert forbidden.risk_level == "critical"
    assert policy.evaluate("patch", "file_change").decision == "allow"


def test_balanced_harness_persists_runs_artifacts_quality_and_unified_events(
    app_factory,
) -> None:
    app = app_factory()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/tasks",
            json={
                "project_id": "test-project",
                "prompt": "Map, implement and independently verify the repository.",
                "harness_profile": "balanced",
                "knowledge_mode": "off",
                "learning_mode": "evaluate",
            },
        )
        assert response.status_code == 202
        task = client.get(f"/api/v1/tasks/{response.json()['id']}").json()
        harness_runs = client.get("/api/v1/harness-runs").json()
        run = harness_runs[0]
        agents = client.get(
            f"/api/v1/harness-runs/{run['id']}/agent-runs"
        ).json()
        quality = client.get("/api/v1/quality").json()
        events = client.get(
            f"/api/v1/tasks/{task['id']}/events",
            params={"follow": False},
        ).text

    assert task["status"] == "completed"
    assert task["harness_profile"] == "balanced"
    assert run["status"] == "completed"
    assert run["max_parallel"] == 3
    assert len(agents) == 7
    assert {agent["role"] for agent in agents} == {
        "repository-mapper",
        "evidence-investigator",
        "alternative-investigator",
        "executor",
        "code-reviewer",
        "security-reviewer",
        "validator",
    }
    assert all(agent["status"] == "completed" for agent in agents)
    assert quality[0]["overall"] == 100.0
    assert "event: harness.started" in events
    assert "event: agent.run.started" in events
    assert "event: harness.completed" in events

    with app.state.database.session_factory() as session:
        assert session.scalar(select(HarnessRun).where(HarnessRun.task_id == task["id"]))
        assert len(list(session.scalars(select(AgentRun)))) == 7
        assert len(list(session.scalars(select(AgentArtifact)))) == 7
        assert len(list(session.scalars(select(QualityScore)))) == 1


def test_fast_harness_agent_and_artifact_endpoints(app_factory) -> None:
    with TestClient(app_factory()) as client:
        task = client.post(
            "/api/v1/tasks",
            json={
                "project_id": "test-project",
                "prompt": "Inspect and validate.",
                "harness_profile": "fast",
                "knowledge_mode": "off",
            },
        ).json()
        run = client.get("/api/v1/harness-runs").json()[0]
        agents = client.get(
            f"/api/v1/harness-runs/{run['id']}/agent-runs"
        ).json()
        agent = client.get(f"/api/v1/agent-runs/{agents[0]['id']}").json()
        artifacts = client.get(
            f"/api/v1/agent-runs/{agents[0]['id']}/artifacts"
        ).json()

        assert client.get("/api/v1/harness-runs/missing").status_code == 404
        assert (
            client.get("/api/v1/harness-runs/missing/agent-runs").status_code
            == 404
        )
        assert client.get("/api/v1/agent-runs/missing").status_code == 404

    assert task["status"] == "queued"
    assert len(agents) == 3
    assert agent["access_mode"] == "read_only"
    assert artifacts[0]["artifact_type"] == "structured-report"
    assert len(artifacts[0]["content_hash"]) == 64


def test_approval_service_persists_policy_decisions_and_resolution(app_factory) -> None:
    app = app_factory()
    with TestClient(app) as client:
        task = client.post(
            "/api/v1/tasks",
            json={
                "project_id": "test-project",
                "prompt": "Create approval test task.",
                "knowledge_mode": "off",
            },
        ).json()
        approval_service = app.state.approval_service
        decision, safe_id = asyncio.run(
            approval_service.request(
                task_id=task["id"],
                agent_run_id=None,
                request_type="command",
                subject="git status",
            )
        )
        denied, denied_id = asyncio.run(
            approval_service.request(
                task_id=task["id"],
                agent_run_id=None,
                request_type="command",
                subject="git reset --hard HEAD",
            )
        )
        with app.state.database.session_factory() as session:
            pending = ApprovalRequest(
                task_id=task["id"],
                request_type="command",
                subject="deploy production",
                risk_level="medium",
                status="pending",
                policy_decision="approval_required",
            )
            session.add(pending)
            session.commit()
            pending_id = pending.id
        resolved = client.post(
            f"/api/v1/approvals/{pending_id}/resolve",
            json={
                "decision": "approve",
                "resolved_by": "test-user",
                "note": "approved in test",
            },
        )
        approvals = client.get(f"/api/v1/tasks/{task['id']}/approvals").json()

        assert client.post(
            "/api/v1/approvals/missing/resolve",
            json={"decision": "deny", "resolved_by": "test-user"},
        ).status_code == 404
        assert client.post(
            f"/api/v1/approvals/{pending_id}/resolve",
            json={"decision": "deny", "resolved_by": "test-user"},
        ).status_code == 409

    assert decision == "accept"
    assert denied == "decline"
    assert safe_id != denied_id
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "approved"
    assert len(approvals) == 3
