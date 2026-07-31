from __future__ import annotations

import time

from fastapi.testclient import TestClient


def wait_for_issue(
    client: TestClient,
    issue_id: str,
    statuses: set[str],
    *,
    timeout_seconds: float = 15,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, object] | None = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/operations/issues/{issue_id}")
        response.raise_for_status()
        last = response.json()
        if last["status"] in statuses:
            return last
        time.sleep(0.03)
    raise AssertionError(
        f"Issue {issue_id} did not reach {sorted(statuses)}; last={last}"
    )


def intake(
    client: TestClient,
    *,
    title: str,
    error_message: str,
    external_event_id: str,
    source_type: str = "api",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/operations/issues/intake",
        json={
            "project_reference": "test-project",
            "source_type": source_type,
            "source_id": "source-1",
            "title": title,
            "error_type": "RuntimeFailure",
            "error_message": error_message,
            "severity": "high",
            "external_event_id": external_event_id,
            "evidence": {
                "request": "knowledge search",
                "token": "must-not-persist",
            },
        },
    )
    assert response.status_code == 202
    return response.json()


def test_issue_center_deduplicates_and_closes_external_failure(
    client: TestClient,
) -> None:
    issue = intake(
        client,
        title="Network share authentication failed",
        error_message=(
            "Credential authentication failed, password=plain-text-secret"
        ),
        external_event_id="supervisor-event-1",
        source_type="knowledge_ingestion",
    )
    duplicate = intake(
        client,
        title="Network share authentication failed",
        error_message=(
            "Credential authentication failed, password=plain-text-secret"
        ),
        external_event_id="supervisor-event-2",
        source_type="knowledge_ingestion",
    )
    assert duplicate["id"] == issue["id"]

    reviewed = wait_for_issue(
        client,
        str(issue["id"]),
        {"waiting_approval"},
    )
    assert reviewed["boundary"] == "credential_or_authorization"
    assert reviewed["occurrence_count"] == 2
    assert "plain-text-secret" not in str(reviewed)
    assert {item["artifact_type"] for item in reviewed["artifacts"]} >= {
        "plan",
        "review",
    }

    approval = client.post(
        f"/api/v1/operations/issues/{issue['id']}/approve",
        json={"resolved_by": "admin", "note": "Credential was rotated"},
    )
    assert approval.status_code == 200
    assert approval.json()["status"] == "waiting_external"

    implementation = client.post(
        f"/api/v1/operations/issues/{issue['id']}/implementations",
        json={
            "implemented_by": "admin",
            "summary": "Rotated the network share credential and verified access.",
            "branch": None,
            "commits": [],
            "validation": [{"command": "share probe", "status": "passed"}],
        },
    )
    assert implementation.status_code == 200
    closed = wait_for_issue(client, str(issue["id"]), {"closed"})
    assert closed["evaluation_status"] == "passed"
    assert closed["closed_by"] == "ai-independent-evaluator"


def test_operations_mutations_require_authenticated_admin_and_skip_deltas(
    client: TestClient,
) -> None:
    issue = intake(
        client,
        title="Controlled event retention validation",
        error_message="Verify admin authentication and compact runtime events",
        external_event_id="operations-security-event-1",
    )
    reviewed = wait_for_issue(
        client,
        str(issue["id"]),
        {"waiting_approval"},
    )

    unauthorized = client.post(
        f"/api/v1/operations/issues/{issue['id']}/approve",
        json={"resolved_by": "spoofed", "note": "unauthorized"},
        headers={
            "X-CAG-Admin-Token": "incorrect",
            "X-CAG-Admin-Identity": "spoofed",
        },
    )
    assert unauthorized.status_code == 401

    service = client.app.state.operational_issue_service
    service._record_runtime_event(
        str(issue["id"]),
        "triage",
        "agent.message.delta",
        {"text": "large cumulative partial message"},
    )
    service._record_runtime_event(
        str(issue["id"]),
        "triage",
        "agent.message",
        {"text": "bounded final message"},
    )
    detail = client.get(
        f"/api/v1/operations/issues/{reviewed['id']}"
    ).json()
    event_types = [event["type"] for event in detail["events"]]
    assert "ai.triage.agent.message.delta" not in event_types
    assert "ai.triage.agent.message" in event_types


def test_internal_issue_uses_approved_improvement_branch(
    client: TestClient,
) -> None:
    issue = intake(
        client,
        title="Knowledge search blocks the Gateway",
        error_message=(
            "Python loaded every knowledge chunk and blocked the event loop"
        ),
        external_event_id="api-scale-event-1",
        source_type="knowledge_search",
    )
    reviewed = wait_for_issue(
        client,
        str(issue["id"]),
        {"waiting_approval"},
    )
    assert reviewed["boundary"] == "cag_internal"

    approval = client.post(
        f"/api/v1/operations/issues/{issue['id']}/approve",
        json={"resolved_by": "admin", "note": "Proceed in an isolated branch"},
    )
    assert approval.status_code == 200
    approved = approval.json()
    assert approved["status"] == "implementing"
    assert approved["improvement_branch"].startswith(
        "codex/improvement/oi-"
    )
    assert approved["implementation_task_id"]

    closed = wait_for_issue(
        client,
        str(issue["id"]),
        {"closed"},
        timeout_seconds=30,
    )
    assert closed["evaluation_status"] == "passed"
    assert {item["artifact_type"] for item in closed["artifacts"]} >= {
        "plan",
        "review",
        "implementation",
        "evaluation",
    }
    queue_status = client.get("/api/v1/queue/status").json()
    assert queue_status["configured_workers"]["operations"] == 1


def test_issue_admin_can_reject_reopen_and_record_evaluation(
    client: TestClient,
) -> None:
    missing = client.get("/api/v1/operations/issues/missing")
    assert missing.status_code == 404

    issue = intake(
        client,
        title="Parser policy regression",
        error_message="Parser returned an unsupported result for source policy",
        external_event_id="parser-event-1",
    )
    reviewed = wait_for_issue(
        client,
        str(issue["id"]),
        {"waiting_approval"},
    )
    rejection = client.post(
        f"/api/v1/operations/issues/{issue['id']}/reject",
        json={"resolved_by": "admin", "note": "Plan requires revision"},
    )
    assert rejection.status_code == 200
    assert rejection.json()["status"] == "rejected"

    invalid_approval = client.post(
        f"/api/v1/operations/issues/{issue['id']}/approve",
        json={"resolved_by": "admin", "note": "late approval"},
    )
    assert invalid_approval.status_code == 409
    invalid_implementation = client.post(
        f"/api/v1/operations/issues/{issue['id']}/implementations",
        json={
            "implemented_by": "admin",
            "summary": "invalid transition",
            "branch": None,
            "commits": [],
            "validation": [],
        },
    )
    assert invalid_implementation.status_code == 409

    reopened = client.post(
        f"/api/v1/operations/issues/{issue['id']}/reopen",
        json={"reopened_by": "admin", "reason": "Updated evidence is available"},
    )
    assert reopened.status_code == 200
    reviewed_again = wait_for_issue(
        client,
        str(issue["id"]),
        {"waiting_approval"},
    )
    assert reviewed_again["occurrence_count"] == reviewed["occurrence_count"]

    failed_evaluation = client.post(
        f"/api/v1/operations/issues/{issue['id']}/evaluations",
        json={
            "evaluated_by": "admin",
            "passed": False,
            "summary": "Original failure still reproduces",
            "metrics": {"replay_count": 1},
        },
    )
    assert failed_evaluation.status_code == 200
    reviewed_third = wait_for_issue(
        client,
        str(issue["id"]),
        {"waiting_approval"},
    )
    passed_evaluation = client.post(
        f"/api/v1/operations/issues/{issue['id']}/evaluations",
        json={
            "evaluated_by": "admin",
            "passed": True,
            "summary": "Original failure no longer reproduces",
            "metrics": {"replay_count": 2},
        },
    )
    assert passed_evaluation.status_code == 200
    assert passed_evaluation.json()["status"] == "closed"

    dashboard = client.get("/api/v1/operations/dashboard")
    filtered = client.get(
        "/api/v1/operations/issues",
        params={"status": "closed", "severity": "high", "limit": 10},
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["total"] >= 1
    assert filtered.status_code == 200
    assert any(item["id"] == issue["id"] for item in filtered.json())


def test_bulk_external_implementation_queues_evaluation(
    client: TestClient,
) -> None:
    issue_ids = []
    for ordinal in (1, 2):
        issue = intake(
            client,
            title=f"External dependency unavailable {ordinal}",
            error_message=f"Network connection timeout for dependency {ordinal}",
            external_event_id=f"external-bulk-{ordinal}",
            source_type="external_connector",
        )
        reviewed = wait_for_issue(
            client,
            str(issue["id"]),
            {"waiting_approval"},
        )
        approval = client.post(
            f"/api/v1/operations/issues/{reviewed['id']}/approve",
            json={"resolved_by": "admin", "note": "Dependency recovered"},
        )
        assert approval.status_code == 200
        issue_ids.append(str(issue["id"]))

    response = client.post(
        "/api/v1/operations/bulk/implementations",
        json={
            "issue_ids": issue_ids,
            "implemented_by": "admin",
            "summary": "Recovered the shared external dependency.",
            "branch": None,
            "commits": [],
            "validation": [{"command": "dependency probe", "status": "passed"}],
        },
    )
    assert response.status_code == 200
    assert len(response.json()) == 2
    for issue_id in issue_ids:
        closed = wait_for_issue(client, issue_id, {"closed"})
        assert closed["evaluation_status"] == "passed"
