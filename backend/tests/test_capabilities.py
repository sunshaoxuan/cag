from pathlib import Path

from fastapi.testclient import TestClient

from app.capabilities.service import CapabilityService
from tests.waiters import wait_for_task


class RepeatedFailureRuntime:
    async def execute(self, **_):
        raise RuntimeError("repeatable investigation failure")


VALID_METRICS = {
    "dependencies_passed": True,
    "permissions_passed": True,
    "supply_chain_passed": True,
    "security_pass_rate": 1.0,
    "architecture_pass_rate": 1.0,
    "replay_count": 20,
    "project_coverage": 2,
    "critical_accuracy_regression": False,
    "quality_gain_percent": 5.5,
    "candidate_success_rate": 0.95,
    "baseline_success_rate": 0.94,
    "p95_time_increase_percent": 7.0,
}


def valid_definition(code: str = "test-capability") -> dict:
    return CapabilityService.default_definition("skill", code)


def propose_skill(client: TestClient, code: str = "test-capability") -> dict:
    response = client.post(
        "/api/v1/capabilities/skills",
        json={
            "code": code,
            "version": "1.0.0",
            "definition": valid_definition(code),
            "source": "test",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_seeded_registry_and_standard_controls(client: TestClient) -> None:
    skills = client.get("/api/v1/capabilities/skills")
    tools = client.get("/api/v1/capabilities/tools")
    validators = client.get("/api/v1/capabilities/validators")
    profiles = client.get("/api/v1/capabilities/harness-profiles")
    controls = client.get("/api/v1/standards/controls")

    assert skills.status_code == 200
    assert {item["code"] for item in skills.json()} >= {
        "repository-map",
        "citation-answering",
    }
    assert any(item["code"] == "pgvector-hybrid-search" for item in tools.json())
    assert any(item["code"] == "secret-scanner" for item in validators.json())
    assert profiles.json()[0]["kind"] == "harness_profile"
    assert len(controls.json()) == 7
    assert all(not item["certification_claimed"] for item in controls.json())


def test_proposal_is_content_idempotent_and_schema_gate_rejects(
    client: TestClient,
) -> None:
    first = propose_skill(client, "idempotent-proposal")
    second = propose_skill(client, "idempotent-proposal")
    assert first["id"] == second["id"]

    unsafe = client.post(
        "/api/v1/capabilities/skills",
        json={
            "code": "unsafe",
            "version": "1",
            "definition": {"raw_prompt": "secret customer material"},
        },
    ).json()
    evaluation = client.post(
        f"/api/v1/evaluations/{unsafe['id']}",
        json={"metrics": VALID_METRICS},
    )
    assert evaluation.status_code == 200
    assert evaluation.json()["passed"] is False
    assert {item["code"] for item in evaluation.json()["findings"]} == {
        "schema_missing_fields",
        "sensitive_content",
    }


def test_full_benchmark_shadow_canary_promotion_writes_receipt(
    settings, app_factory, tmp_path: Path
) -> None:
    settings.self_improvement_root = tmp_path / "selfimp"
    with TestClient(app_factory()) as client:
        asset = propose_skill(client, "promotable")
        evaluation = client.post(
            f"/api/v1/evaluations/{asset['id']}",
            json={"metrics": VALID_METRICS},
        )
        assert evaluation.json()["passed"] is True
        benchmark_promotions = client.get("/api/v1/promotions").json()
        assert all(
            item["evidence"]["evaluation_id"] == evaluation.json()["id"]
            for item in benchmark_promotions
            if item["to_status"] in {"validated", "benchmarked"}
        )
        for index in range(10):
            shadow = client.post(
                f"/api/v1/promotions/{asset['id']}/shadow",
                json={
                    "passed": True,
                    "metrics": {"project_coverage": 2, "run": index + 1},
                },
            )
            assert shadow.status_code == 200
        assert shadow.json()["status"] == "canary"
        for index in range(5):
            canary = client.post(
                f"/api/v1/promotions/{asset['id']}/canary",
                json={"passed": True, "metrics": {"run": index + 1}},
            )
            assert canary.status_code == 200
        assert canary.json()["status"] == "active"
        assert canary.json()["active"] is True

        promotions = client.get("/api/v1/promotions").json()
        active = next(item for item in promotions if item["to_status"] == "active")
        receipt = Path(active["receipt_path"])
        assert receipt.is_file()
        assert "current-agent-gateway" in receipt.read_text(encoding="utf-8")


def test_canary_failures_and_quality_regression_auto_rollback(
    client: TestClient,
) -> None:
    asset = propose_skill(client, "rollback-on-failure")
    client.post(
        f"/api/v1/evaluations/{asset['id']}",
        json={"metrics": VALID_METRICS},
    )
    for _ in range(10):
        client.post(
            f"/api/v1/promotions/{asset['id']}/shadow",
            json={"passed": True},
        )
    first = client.post(
        f"/api/v1/promotions/{asset['id']}/canary",
        json={"passed": False},
    )
    second = client.post(
        f"/api/v1/promotions/{asset['id']}/canary",
        json={"passed": False},
    )
    assert first.json()["status"] == "canary"
    assert second.json()["status"] == "benchmarked"
    assert any(
        "consecutive" in item["reason"].lower()
        for item in client.get("/api/v1/rollbacks").json()
    )

    quality_asset = propose_skill(client, "rollback-on-quality")
    client.post(
        f"/api/v1/evaluations/{quality_asset['id']}",
        json={"metrics": VALID_METRICS},
    )
    result = client.post(
        f"/api/v1/promotions/{quality_asset['id']}/shadow",
        json={"passed": True, "metrics": {"quality_delta_percent": -5.1}},
    )
    assert result.json()["status"] == "benchmarked"


def test_manual_rollback_gardeners_and_api_errors(client: TestClient) -> None:
    asset = propose_skill(client, "manual-rollback")
    rollback = client.post(
        f"/api/v1/rollbacks/{asset['id']}",
        json={"reason": "validator dependency expired"},
    )
    assert rollback.status_code == 200
    assert rollback.json()["restored_status"] == "benchmarked"
    gardeners = client.post("/api/v1/gardeners/run")
    assert gardeners.status_code == 200
    assert {item["gardener"] for item in gardeners.json()} == {
        "doc-gardener",
        "skill-gardener",
        "tool-gardener",
        "memory-gardener",
    }
    assert client.post(
        "/api/v1/evaluations/missing",
        json={"metrics": VALID_METRICS},
    ).status_code == 404
    assert client.post(
        "/api/v1/promotions/missing/shadow",
        json={"passed": True},
    ).status_code == 404
    assert client.post(
        "/api/v1/rollbacks/missing",
        json={"reason": "missing asset"},
    ).status_code == 404


def test_task_learning_proposes_candidate_after_three_successes(
    client: TestClient,
) -> None:
    for _ in range(3):
        created = client.post(
            "/api/v1/tasks",
            json={
                "project_id": "test-project",
                "prompt": "trace the stable service call chain",
                "learning_mode": "evaluate",
            },
        )
        assert created.status_code == 202
        task = wait_for_task(client, created.json()["id"])
        assert task["status"] == "completed"

    skills = client.get("/api/v1/capabilities/skills").json()
    learned = [item for item in skills if item["source"] == "task-learning"]
    assert len(learned) == 1
    response = client.get(f"/api/v1/tasks/{created.json()['id']}/events")
    assert "learning.candidate.proposed" in response.text


def test_task_learning_proposes_failure_candidate_after_two_failures(
    app_factory,
) -> None:
    with TestClient(app_factory(RepeatedFailureRuntime())) as client:
        for _ in range(2):
            created = client.post(
                "/api/v1/tasks",
                json={
                    "project_id": "test-project",
                    "prompt": "repeatable failed investigation",
                    "learning_mode": "capture",
                },
            )
            assert created.status_code == 202
            task = wait_for_task(client, created.json()["id"])
            assert task["status"] == "failed"

        learned = [
            item
            for item in client.get("/api/v1/capabilities/skills").json()
            if item["source"] == "task-learning"
        ]
        assert len(learned) == 1
