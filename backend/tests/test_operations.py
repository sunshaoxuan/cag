from __future__ import annotations

from dataclasses import replace
import json
import time

from fastapi.testclient import TestClient

from app.runtimes.fake import FakeAgentRuntime


class ReviewDecisionRuntime(FakeAgentRuntime):
    def __init__(self, review_summary: str) -> None:
        super().__init__()
        self._review_summary = review_summary

    async def execute(self, **kwargs):
        result = await super().execute(**kwargs)
        if '"blocking_findings"' in str(kwargs["prompt"]):
            return replace(result, summary=self._review_summary)
        return result


class PlanDecisionRuntime(FakeAgentRuntime):
    def __init__(self, plan_summary: str) -> None:
        super().__init__()
        self._plan_summary = plan_summary

    async def execute(self, **kwargs):
        result = await super().execute(**kwargs)
        prompt = str(kwargs["prompt"])
        if (
            '"resolution_mode_reason"' in prompt
            and '"blocking_findings"' not in prompt
        ):
            return replace(result, summary=self._plan_summary)
        return result


class FailingOperationalRuntime(FakeAgentRuntime):
    async def execute(self, **kwargs):
        raise ValueError("Separator is not found, and chunk exceed the limit")


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
    assert reviewed["decision_brief"]["administrator_language"] == "zh-CN"
    assert "故障" in reviewed["decision_brief"]["problem_summary"]
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
    monkeypatch,
) -> None:
    service = client.app.state.operational_issue_service
    workspace_manager = service._workspace_manager
    original_prepare = workspace_manager.prepare
    workspace_task_ids: list[str] = []

    def record_prepare(*, project, task_id):
        workspace_task_ids.append(task_id)
        return original_prepare(project=project, task_id=task_id)

    monkeypatch.setattr(workspace_manager, "prepare", record_prepare)

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
    assert len(workspace_task_ids) == 3
    assert len(set(workspace_task_ids)) == 3
    assert all("-s" in task_id for task_id in workspace_task_ids)

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


def test_review_blockers_require_plan_revision_and_prevent_approval(
    app_factory,
) -> None:
    review = json.dumps(
        {
            "administrator_language": "zh-CN",
            "summary": "该方案需要完成一项有边界的修正。",
            "root_cause_assessment": "现有根因证据足以支持本轮判断。",
            "recommendation": "revise",
            "blocking_findings": [
                {
                    "code": "B1",
                    "severity": "high",
                    "title": "缺少并发门禁",
                    "finding": "当前并发执行没有明确上限。",
                    "required_change": "增加数据库支持的单任务门禁。",
                }
            ],
            "approval_conditions": ["完成 B1 修正。"],
            "validation_plan": ["执行并发运行测试。"],
            "warnings": [],
        }
    )
    with TestClient(
        app_factory(ReviewDecisionRuntime(review)),
        headers={
            "X-CAG-Admin-Token": "test-operations-admin-token",
            "X-CAG-Admin-Identity": "review-admin",
        },
    ) as local_client:
        issue = intake(
            local_client,
            title="Concurrent operational work",
            error_message="Operational processing requires a concurrency gate",
            external_event_id="review-revise-1",
        )
        reviewed = wait_for_issue(
            local_client,
            str(issue["id"]),
            {"plan_revision_required"},
        )
        assert reviewed["resolution_mode"] == "agent_self_improvement"
        assert reviewed["review_recommendation"] == "revise"
        assert reviewed["blocking_finding_count"] == 1
        assert reviewed["decision_brief"]["approval_ready"] is False
        assert reviewed["decision_brief"]["blocking_findings"][0]["code"] == "B1"

        approval = local_client.post(
            f"/api/v1/operations/issues/{issue['id']}/approve",
            json={"note": "approve despite blocker"},
        )
        assert approval.status_code == 409


def test_malformed_review_fails_closed_with_visible_decision_brief(
    app_factory,
) -> None:
    with TestClient(
        app_factory(ReviewDecisionRuntime("review output without JSON")),
        headers={
            "X-CAG-Admin-Token": "test-operations-admin-token",
            "X-CAG-Admin-Identity": "review-admin",
        },
    ) as local_client:
        issue = intake(
            local_client,
            title="Malformed reviewer output",
            error_message="Reviewer response cannot be parsed",
            external_event_id="review-malformed-1",
        )
        reviewed = wait_for_issue(
            local_client,
            str(issue["id"]),
            {"plan_revision_required"},
        )
        assert reviewed["review_recommendation"] == "revise"
        assert reviewed["blocking_finding_count"] == 1
        assert reviewed["decision_brief"]["administrator_language"] == "zh-CN"
        assert "简体中文" in reviewed["decision_brief"]["review_summary"]
        finding = reviewed["decision_brief"]["blocking_findings"][0]
        assert finding["code"] == "STRUCTURED_REVIEW_REQUIRED"
        assert "审核记录要求" in finding["title"]


def test_human_code_route_waits_for_manual_implementation(
    app_factory,
) -> None:
    plan = json.dumps(
        {
            "administrator_language": "zh-CN",
            "problem_summary": "受保护的部署钩子需要修正。",
            "impact_summary": "当前发布无法通过生产门禁。",
            "root_cause_summary": "该钩子属于受保护的工程路径。",
            "root_cause_confidence": 0.92,
            "improvement_goal": "在人工工程控制下修正该钩子。",
            "resolution_mode": "human_code_change",
            "resolution_mode_reason": (
                "该变更需要直接的工程权限和人工监督。"
            ),
            "resolution_mode_confidence": 0.95,
            "proposed_changes": [
                {
                    "area": "backend/app/api/health.py",
                    "change": "由人工实施经过审核的代码修正。",
                    "reason": "受保护路径不能直接委派给 Agent。",
                }
            ],
            "validation_plan": ["执行受保护部署路径的验收测试。"],
            "rollback_plan": ["恢复上一版已签名的部署钩子。"],
            "administrator_actions": ["指派具备权限的工程师。"],
            "boundary": "cag_internal",
            "boundary_confidence": 0.96,
        }
    )
    with TestClient(
        app_factory(PlanDecisionRuntime(plan)),
        headers={
            "X-CAG-Admin-Token": "test-operations-admin-token",
            "X-CAG-Admin-Identity": "review-admin",
        },
    ) as local_client:
        issue = intake(
            local_client,
            title="Protected deployment hook",
            error_message="A privileged deployment hook failed validation",
            external_event_id="human-code-route-1",
        )
        reviewed = wait_for_issue(
            local_client,
            str(issue["id"]),
            {"waiting_approval"},
        )
        assert reviewed["resolution_mode"] == "human_code_change"
        filtered = local_client.get(
            "/api/v1/operations/issues",
            params={"resolution_mode": "human_code_change"},
        )
        assert filtered.status_code == 200
        assert [item["id"] for item in filtered.json()] == [issue["id"]]
        dashboard = local_client.get("/api/v1/operations/dashboard").json()
        assert dashboard["by_resolution_mode"]["human_code_change"] == 1
        approval = local_client.post(
            f"/api/v1/operations/issues/{issue['id']}/approve",
            json={"note": "Assign to platform engineering"},
        )
        assert approval.status_code == 200
        assert approval.json()["status"] == "waiting_external"
        assert approval.json()["implementation_task_id"] is None


def test_english_administrator_summary_fails_closed_to_chinese_brief(
    app_factory,
) -> None:
    english_plan = json.dumps(
        {
            "administrator_language": "zh-CN",
            "problem_summary": "The gateway health check failed.",
            "impact_summary": "Requests may be unavailable.",
            "root_cause_summary": "The initiating cause is unknown.",
            "root_cause_confidence": 0.4,
            "improvement_goal": "Collect evidence before changing behavior.",
            "resolution_mode": "mixed",
            "resolution_mode_reason": "Operator evidence and code analysis are required.",
            "resolution_mode_confidence": 0.8,
            "proposed_changes": [
                {
                    "area": "diagnostics",
                    "change": "Collect bounded diagnostic evidence.",
                    "reason": "The current evidence is incomplete.",
                }
            ],
            "validation_plan": ["Verify the diagnostic record."],
            "rollback_plan": ["Keep the previous behavior."],
            "administrator_actions": ["Approve evidence collection."],
            "boundary": "cag_internal",
            "boundary_confidence": 0.8,
        }
    )
    with TestClient(
        app_factory(PlanDecisionRuntime(english_plan)),
        headers={
            "X-CAG-Admin-Token": "test-operations-admin-token",
            "X-CAG-Admin-Identity": "review-admin",
        },
    ) as local_client:
        issue = intake(
            local_client,
            title="English administrator summary",
            error_message="The generated summary ignored the requested language",
            external_event_id="english-summary-1",
        )
        reviewed = wait_for_issue(
            local_client,
            str(issue["id"]),
            {"plan_revision_required"},
        )
        brief = reviewed["decision_brief"]
        assert brief["administrator_language"] == "zh-CN"
        assert "问题中心收到" in brief["problem_summary"]
        assert "结构化简体中文校验" in brief["resolution_mode_reason"]
        assert brief["approval_ready"] is False


def test_operational_runtime_failure_creates_chinese_decision_brief(
    app_factory,
) -> None:
    with TestClient(
        app_factory(FailingOperationalRuntime()),
        headers={
            "X-CAG-Admin-Token": "test-operations-admin-token",
            "X-CAG-Admin-Identity": "review-admin",
        },
    ) as local_client:
        issue = intake(
            local_client,
            title="Operational output exceeded transport limit",
            error_message="The operational planner could not finish",
            external_event_id="operational-runtime-failure-1",
        )
        failed = wait_for_issue(
            local_client,
            str(issue["id"]),
            {"triage_failed"},
        )
        brief = failed["decision_brief"]
        assert brief["administrator_language"] == "zh-CN"
        assert "问题处理运行时" in brief["problem_summary"]
        assert "Separator is not found" in brief["root_cause_summary"]
        assert brief["resolution_mode"] == "undetermined"
        assert brief["approval_ready"] is False
        assert brief["blocking_findings"][0]["code"] == (
            "RUNTIME_PROCESSING_FAILED"
        )
        assert "请查看折叠日志" in failed["required_human_input"]
