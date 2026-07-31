from __future__ import annotations

import asyncio
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select, update

from app.database import Database
from app.models import (
    KnowledgeIngestion,
    KnowledgeSource,
    OperationalIssue,
    OperationalIssueArtifact,
    OperationalIssueEvent,
    OperationalIssueOccurrence,
    OperationalIssueStatus,
    Project,
    QueueItem,
    QueueItemStatus,
    Task,
)
from app.models.base import utc_now
from app.projects.registry import ProjectRegistry
from app.operations.schemas import OperationalPlan, OperationalReview
from app.runtimes.base import AgentRuntime, RuntimeResult
from app.services.task_service import TaskService
from app.workspaces.manager import WorkspaceManager


BOUNDARY_INTERNAL = "cag_internal"
BOUNDARY_EXTERNAL = "external_dependency"
BOUNDARY_CREDENTIAL = "credential_or_authorization"
BOUNDARY_SCOPE = "policy_or_scope"

RESOLUTION_AGENT = "agent_self_improvement"
RESOLUTION_HUMAN_CODE = "human_code_change"
RESOLUTION_EXTERNAL = "external_operator_action"
RESOLUTION_MIXED = "mixed"
RESOLUTION_OUT_OF_SCOPE = "out_of_scope"
RESOLUTION_UNDETERMINED = "undetermined"

OperationsModel = TypeVar("OperationsModel", bound=BaseModel)

SECRET_PATTERNS = (
    re.compile(r"(?i)(password|secret|token|api[_ -]?key)\s*[:=]\s*\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
)


class OperationalIssueService:
    def __init__(
        self,
        *,
        database: Database,
        runtime: AgentRuntime,
        project_registry: ProjectRegistry,
        task_service: TaskService,
        workspace_manager: WorkspaceManager,
    ) -> None:
        self._database = database
        self._runtime = runtime
        self._project_registry = project_registry
        self._task_service = task_service
        self._workspace_manager = workspace_manager

    def capture(
        self,
        *,
        project_reference: str,
        source_type: str,
        title: str,
        error_message: str,
        error_type: str | None = None,
        source_id: str | None = None,
        severity: str = "medium",
        evidence: dict[str, Any] | None = None,
        external_event_id: str | None = None,
        event_type: str = "failure",
        parent_issue_id: str | None = None,
    ) -> OperationalIssue:
        clean_message = self._sanitize_text(error_message)[:20_000]
        clean_evidence = self._sanitize_value(evidence or {})
        with self._database.session_factory() as session:
            if external_event_id:
                occurrence = session.scalar(
                    select(OperationalIssueOccurrence).where(
                        OperationalIssueOccurrence.external_event_id
                        == external_event_id
                    )
                )
                if occurrence is not None:
                    issue = session.get(OperationalIssue, occurrence.issue_id)
                    if issue is None:
                        raise RuntimeError("Operational issue occurrence is orphaned")
                    return issue

            project = self._task_service.resolve_project(
                session,
                project_reference,
            )
            fingerprint = self._fingerprint(
                project.id,
                source_type,
                error_type,
                clean_message,
            )
            issue = session.scalar(
                select(OperationalIssue)
                .where(
                    OperationalIssue.project_id == project.id,
                    OperationalIssue.fingerprint == fingerprint,
                )
                .with_for_update()
            )
            now = utc_now()
            created = issue is None
            if issue is None:
                issue = OperationalIssue(
                    project_id=project.id,
                    parent_issue_id=parent_issue_id,
                    code=f"OI-{uuid4().hex[:10].upper()}",
                    fingerprint=fingerprint,
                    source_type=source_type,
                    source_id=source_id,
                    title=title[:255],
                    summary=clean_message,
                    severity=severity,
                    evidence=clean_evidence,
                    first_seen_at=now,
                    last_seen_at=now,
                )
                session.add(issue)
                session.flush()
            else:
                issue.occurrence_count += 1
                issue.last_seen_at = now
                issue.summary = clean_message
                issue.evidence = {
                    **(issue.evidence or {}),
                    **clean_evidence,
                }
                if issue.status in OperationalIssueStatus.TERMINAL:
                    issue.status = OperationalIssueStatus.DETECTED
                    issue.closed_at = None
                    issue.closed_by = None
                    issue.resolution = None
                    issue.approval_status = "not_requested"
                    issue.evaluation_status = "not_started"
                    issue.review_recommendation = None
                    issue.blocking_finding_count = 0
                    issue.decision_brief = {}

            session.add(
                OperationalIssueOccurrence(
                    issue_id=issue.id,
                    external_event_id=external_event_id,
                    event_type=event_type,
                    error_type=error_type,
                    error_message=clean_message,
                    evidence=clean_evidence,
                    occurred_at=now,
                )
            )
            self._append_event(
                session,
                issue,
                "issue.detected" if created else "issue.reoccurred",
                {
                    "source_type": source_type,
                    "source_id": source_id,
                    "severity": severity,
                    "occurrence_count": issue.occurrence_count,
                },
            )
            self._enqueue(
                session,
                issue,
                job_type="operational_triage",
                priority=self._priority(severity),
            )
            session.commit()
            session.refresh(issue)
            return issue

    async def process(self, issue_id: str, job_type: str) -> None:
        if job_type == "operational_triage":
            await self._triage(issue_id)
            return
        if job_type == "operational_evaluation":
            await self._evaluate(issue_id)
            return
        raise RuntimeError(f"Unsupported operational job type: {job_type}")

    async def _triage(self, issue_id: str) -> None:
        with self._database.session_factory() as session:
            issue = session.get(OperationalIssue, issue_id)
            if issue is None:
                return
            issue.status = OperationalIssueStatus.TRIAGING
            self._append_event(session, issue, "issue.triage.started", {})
            project = session.get(Project, issue.project_id)
            if project is None:
                raise RuntimeError("Operational issue project is unavailable")
            project_code = project.code
            evidence = {
                "code": issue.code,
                "source_type": issue.source_type,
                "source_id": issue.source_id,
                "title": issue.title,
                "summary": issue.summary,
                "severity": issue.severity,
                "occurrence_count": issue.occurrence_count,
                "evidence": issue.evidence,
            }
            occurrence_count = issue.occurrence_count
            session.commit()

        project_config = self._project_registry.get_by_code(project_code)
        if project_config is None:
            raise RuntimeError("Operational issue project configuration is unavailable")
        workspace = await asyncio.to_thread(
            self._workspace_manager.prepare,
            project=project_config,
            task_id=f"op-{issue_id[:8]}-t{occurrence_count}",
        )
        analysis = await self._run_ai(
            issue_id=issue_id,
            phase="triage",
            project_code=project_code,
            workspace_path=workspace.path,
            prompt=(
                "You are the CAG operational issue triage and improvement planner. "
                "Work read-only. Classify the responsibility boundary, identify "
                "root cause evidence, decide whether Agent self-improvement can "
                "complete the code change or human engineering is required, propose "
                "a bounded improvement plan, acceptance tests, rollback, and any "
                "administrator input. Do not modify files. Return exactly one JSON "
                "object matching this JSON Schema. Do not wrap the JSON in Markdown.\n"
                f"{json.dumps(OperationalPlan.model_json_schema(), ensure_ascii=False)}\n"
                f"Issue evidence:\n{json.dumps(evidence, ensure_ascii=False, indent=2)}"
            ),
        )
        try:
            structured_plan = self._parse_runtime_model(
                analysis,
                OperationalPlan,
            )
            plan_parse_error = None
        except ValueError as exc:
            structured_plan = None
            plan_parse_error = str(exc)

        if structured_plan is None:
            boundary, confidence, required_input, allowed_actions = (
                self._classify(evidence, analysis)
            )
            resolution_mode = self._default_resolution_mode(boundary)
            resolution_confidence = min(confidence, 0.5)
            resolution_reason = (
                "The planner output did not satisfy the decision schema. "
                "A new structured plan is required before implementation approval."
            )
            plan = {
                "structured_output_valid": False,
                "parse_error": plan_parse_error,
                "problem_summary": evidence["summary"],
                "impact_summary": (
                    f"Severity {evidence['severity']} issue observed "
                    f"{evidence['occurrence_count']} time(s)."
                ),
                "root_cause_summary": (
                    analysis.root_cause
                    or "Root cause is not confirmed by structured evidence."
                ),
                "root_cause_confidence": 0.0,
                "improvement_goal": (
                    "Produce a valid, bounded and reviewable improvement plan."
                ),
                "resolution_mode": resolution_mode,
                "resolution_mode_reason": resolution_reason,
                "resolution_mode_confidence": resolution_confidence,
                "proposed_changes": analysis.changes,
                "validation_plan": analysis.validation,
                "rollback_plan": analysis.next_actions,
                "administrator_actions": [],
                "boundary": boundary,
                "boundary_confidence": confidence,
                "raw_runtime_report": analysis.to_report(),
            }
        else:
            boundary = structured_plan.boundary
            confidence = structured_plan.boundary_confidence
            resolution_mode = self._reconcile_resolution_mode(
                boundary,
                structured_plan.resolution_mode,
            )
            resolution_confidence = (
                structured_plan.resolution_mode_confidence
            )
            resolution_reason = structured_plan.resolution_mode_reason
            required_input = self._required_human_input(
                boundary=boundary,
                resolution_mode=resolution_mode,
                administrator_actions=structured_plan.administrator_actions,
            )
            allowed_actions = self._actions_for_resolution(
                boundary,
                resolution_mode,
            )
            plan = {
                "structured_output_valid": True,
                **structured_plan.model_dump(),
                "resolution_mode": resolution_mode,
            }
        review = await self._run_ai(
            issue_id=issue_id,
            phase="review",
            project_code=project_code,
            workspace_path=workspace.path,
            prompt=(
                "You are an independent CAG architecture, security, data migration, "
                "and regression reviewer. Work read-only. Review the proposed plan, "
                "identify blocking findings and missing acceptance tests, then give "
                "an explicit approval recommendation. Unknown, malformed, incomplete "
                "or contradictory evidence must result in revise. Do not modify files. "
                "Return exactly one JSON object matching this JSON Schema. Do not wrap "
                "the JSON in Markdown.\n"
                f"{json.dumps(OperationalReview.model_json_schema(), ensure_ascii=False)}\n"
                f"Evidence:\n{json.dumps(evidence, ensure_ascii=False, indent=2)}\n"
                f"Plan:\n{json.dumps(plan, ensure_ascii=False, indent=2)}"
            ),
        )
        try:
            structured_review = self._parse_runtime_model(
                review,
                OperationalReview,
            )
            review_parse_error = None
        except ValueError as exc:
            structured_review = None
            review_parse_error = str(exc)

        if structured_review is None:
            review_payload = {
                "structured_output_valid": False,
                "parse_error": review_parse_error,
                "summary": (
                    "The independent review output was not structurally valid. "
                    "The plan requires revision before approval."
                ),
                "root_cause_assessment": (
                    review.root_cause
                    or "No validated structured assessment is available."
                ),
                "recommendation": "revise",
                "blocking_findings": [
                    {
                        "code": "STRUCTURED_REVIEW_REQUIRED",
                        "severity": "critical",
                        "title": "Independent review output is invalid",
                        "finding": review_parse_error or "Malformed review output",
                        "required_change": (
                            "Run the independent review again and persist a valid "
                            "decision object."
                        ),
                    }
                ],
                "approval_conditions": [],
                "validation_plan": [],
                "warnings": review.warnings,
                "raw_runtime_report": review.to_report(),
            }
        else:
            review_payload = {
                "structured_output_valid": True,
                **structured_review.model_dump(),
            }
        blocking_findings = list(
            review_payload.get("blocking_findings") or []
        )
        recommendation = str(review_payload["recommendation"])
        approval_ready = (
            structured_plan is not None
            and structured_review is not None
            and recommendation == "approve"
            and not blocking_findings
            and resolution_mode
            in {
                RESOLUTION_AGENT,
                RESOLUTION_HUMAN_CODE,
                RESOLUTION_EXTERNAL,
                RESOLUTION_MIXED,
            }
        )
        decision_brief = {
            "problem_summary": plan["problem_summary"],
            "impact_summary": plan["impact_summary"],
            "root_cause_summary": plan["root_cause_summary"],
            "root_cause_confidence": plan["root_cause_confidence"],
            "improvement_goal": plan["improvement_goal"],
            "resolution_mode": resolution_mode,
            "resolution_mode_reason": resolution_reason,
            "resolution_mode_confidence": resolution_confidence,
            "recommended_changes": plan["proposed_changes"],
            "validation_plan": self._merge_string_lists(
                plan["validation_plan"],
                review_payload.get("validation_plan") or [],
            ),
            "rollback_plan": plan["rollback_plan"],
            "administrator_actions": plan["administrator_actions"],
            "review_summary": review_payload["summary"],
            "review_recommendation": recommendation,
            "blocking_findings": blocking_findings,
            "approval_conditions": review_payload.get(
                "approval_conditions"
            ) or [],
            "approval_ready": approval_ready,
        }
        with self._database.session_factory() as session:
            issue = session.get(OperationalIssue, issue_id)
            if issue is None:
                return
            issue.boundary = boundary
            issue.boundary_confidence = confidence
            issue.required_human_input = required_input
            issue.allowed_actions = allowed_actions
            issue.resolution_mode = resolution_mode
            issue.resolution_mode_confidence = resolution_confidence
            issue.resolution_mode_reason = resolution_reason
            issue.decision_brief = decision_brief
            issue.review_recommendation = recommendation
            issue.blocking_finding_count = len(blocking_findings)
            if boundary == BOUNDARY_SCOPE and structured_plan is not None:
                issue.approval_status = "not_requested"
                issue.status = OperationalIssueStatus.OUT_OF_SCOPE
            elif approval_ready:
                issue.approval_status = "pending"
                issue.status = OperationalIssueStatus.WAITING_APPROVAL
            else:
                issue.approval_status = "revision_required"
                issue.status = OperationalIssueStatus.PLAN_REVISION_REQUIRED
            self._add_artifact(session, issue, "plan", plan, "ai-planner")
            self._add_artifact(
                session,
                issue,
                "review",
                review_payload,
                "ai-independent-reviewer",
            )
            self._append_event(
                session,
                issue,
                "issue.review.completed",
                {
                    "boundary": boundary,
                    "confidence": confidence,
                    "recommendation": recommendation,
                    "blocking_finding_count": len(blocking_findings),
                    "resolution_mode": resolution_mode,
                    "approval_ready": approval_ready,
                    "status": issue.status,
                },
            )
            session.commit()

    async def _evaluate(self, issue_id: str) -> None:
        with self._database.session_factory() as session:
            issue = session.get(OperationalIssue, issue_id)
            if issue is None:
                return
            issue.status = OperationalIssueStatus.EVALUATING
            issue.evaluation_status = "running"
            self._append_event(session, issue, "issue.evaluation.started", {})
            project = session.get(Project, issue.project_id)
            task = (
                session.get(Task, issue.implementation_task_id)
                if issue.implementation_task_id
                else None
            )
            project_code = project.code if project is not None else ""
            workspace_path = task.workspace_path if task is not None else None
            evidence = {
                "issue": self._issue_summary(issue),
                "implementation": (
                    task.final_report if task is not None else issue.evidence
                ),
                "workspace_path": workspace_path,
            }
            session.commit()

        project_config = self._project_registry.get_by_code(project_code)
        if project_config is None:
            raise RuntimeError("Evaluation project configuration is unavailable")
        if workspace_path is None:
            workspace = await asyncio.to_thread(
                self._workspace_manager.prepare,
                project=project_config,
                task_id=f"op-{issue_id[:8]}-e",
            )
            active_workspace = workspace.path
        else:
            active_workspace = Path(workspace_path)
        result = await self._run_ai(
            issue_id=issue_id,
            phase="evaluation",
            project_code=project_code,
            workspace_path=active_workspace,
            prompt=(
                "Independently evaluate whether the operational improvement resolves "
                "the original failure. Work read-only. Replay the original scenario "
                "when safe, inspect tests and evidence, check regressions, performance, "
                "security, migration, and rollback readiness. Report explicit pass or "
                "fail validation records. Do not modify files. "
                f"Evaluation evidence:\n"
                f"{json.dumps(evidence, ensure_ascii=False, indent=2, default=str)}"
            ),
        )
        passed = bool(result.validation) and all(
            str(item.get("status", "")).lower()
            in {"passed", "success", "completed"}
            for item in result.validation
        )
        evaluation = {
            **result.to_report(),
            "passed": passed,
            "evaluated_by": "ai-independent-evaluator",
        }
        with self._database.session_factory() as session:
            issue = session.get(OperationalIssue, issue_id)
            if issue is None:
                return
            self._add_artifact(
                session,
                issue,
                "evaluation",
                evaluation,
                "ai-independent-evaluator",
            )
            issue.evaluation_status = "passed" if passed else "failed"
            if passed:
                issue.status = OperationalIssueStatus.CLOSED
                issue.resolution = result.summary
                issue.closed_by = "ai-independent-evaluator"
                issue.closed_at = utc_now()
                event_type = "issue.closed"
            else:
                issue.status = OperationalIssueStatus.DETECTED
                issue.approval_status = "not_requested"
                issue.closed_at = None
                self._enqueue(
                    session,
                    issue,
                    job_type="operational_triage",
                    priority=self._priority(issue.severity),
                )
                event_type = "issue.evaluation.failed"
            self._append_event(
                session,
                issue,
                event_type,
                {
                    "passed": passed,
                    "summary": result.summary,
                },
            )
            session.commit()

    def approve(
        self,
        issue_id: str,
        *,
        approved_by: str,
        note: str | None,
    ) -> OperationalIssue:
        with self._database.session_factory() as session:
            issue = session.get(OperationalIssue, issue_id)
            if issue is None:
                raise KeyError(issue_id)
            if issue.status != OperationalIssueStatus.WAITING_APPROVAL:
                raise ValueError("Issue is not waiting for approval")
            if (
                issue.review_recommendation != "approve"
                or issue.blocking_finding_count != 0
                or not bool((issue.decision_brief or {}).get("approval_ready"))
            ):
                raise ValueError(
                    "Independent review has not cleared this issue for approval"
                )
            issue.approval_status = "approved"
            issue.approved_by = approved_by
            issue.approval_note = note
            issue.approved_at = utc_now()
            self._append_event(
                session,
                issue,
                "issue.approved",
                {"approved_by": approved_by, "note": note},
            )
            if (
                issue.boundary in {BOUNDARY_EXTERNAL, BOUNDARY_CREDENTIAL}
                or issue.resolution_mode
                in {
                    RESOLUTION_HUMAN_CODE,
                    RESOLUTION_EXTERNAL,
                    RESOLUTION_MIXED,
                }
            ):
                issue.status = OperationalIssueStatus.WAITING_EXTERNAL
                session.commit()
                session.refresh(issue)
                return issue
            project = session.get(Project, issue.project_id)
            if project is None:
                raise RuntimeError("Issue project is unavailable")
            plan = self._latest_artifact_content(session, issue.id, "plan")
            review = self._latest_artifact_content(session, issue.id, "review")
            project_code = project.code
            branch = f"codex/improvement/{issue.code.lower()}"
            prompt = (
                f"Implement approved operational issue {issue.code}: {issue.title}.\n"
                "Use the approved plan and address every independent review finding. "
                "Run targeted and regression tests. Commit the verified changes on the "
                f"prepared improvement branch {branch}. Do not push or merge it. "
                "Record acceptance and rollback evidence.\n"
                f"Plan:\n{json.dumps(plan, ensure_ascii=False, indent=2)}\n"
                f"Review:\n{json.dumps(review, ensure_ascii=False, indent=2)}"
            )
            issue.status = OperationalIssueStatus.IMPLEMENTING
            issue.improvement_branch = branch
            session.commit()

        request_id = str(uuid4())
        request_hash = sha256(prompt.encode("utf-8")).hexdigest()
        with self._database.session_factory() as session:
            task = self._task_service.create_task(
                session,
                project_reference=project_code,
                prompt=prompt,
                conversation_id=None,
                runtime_profile="self-improvement-candidate",
                client_request_id=request_id,
                request_hash=request_hash,
                trigger_source="operational_issue_center",
                client_id="cag-self-operations",
                idempotency_key=f"issue-implementation:{issue_id}",
                request_metadata={
                    "operational_issue_id": issue_id,
                    "improvement_branch": branch,
                    "approval_by": approved_by,
                },
                knowledge_mode="assist",
                harness_profile="balanced",
                learning_mode="evaluate",
            )
        with self._database.session_factory() as session:
            issue = session.get(OperationalIssue, issue_id)
            if issue is None:
                raise KeyError(issue_id)
            issue.implementation_task_id = task.id
            self._append_event(
                session,
                issue,
                "issue.implementation.queued",
                {"task_id": task.id, "branch": branch},
            )
            session.commit()
            session.refresh(issue)
            return issue

    def reject(
        self,
        issue_id: str,
        *,
        resolved_by: str,
        note: str,
    ) -> OperationalIssue:
        with self._database.session_factory() as session:
            issue = session.get(OperationalIssue, issue_id)
            if issue is None:
                raise KeyError(issue_id)
            if issue.status != OperationalIssueStatus.WAITING_APPROVAL:
                raise ValueError("Issue is not waiting for approval")
            issue.approval_status = "rejected"
            issue.status = OperationalIssueStatus.REJECTED
            issue.resolution = note
            issue.closed_by = resolved_by
            issue.closed_at = utc_now()
            self._append_event(
                session,
                issue,
                "issue.rejected",
                {"resolved_by": resolved_by, "note": note},
            )
            session.commit()
            session.refresh(issue)
            return issue

    def record_manual_implementation(
        self,
        issue_id: str,
        *,
        implemented_by: str,
        summary: str,
        branch: str | None,
        commits: list[str],
        validation: list[dict[str, Any]],
    ) -> OperationalIssue:
        with self._database.session_factory() as session:
            issue = session.get(OperationalIssue, issue_id)
            if issue is None:
                raise KeyError(issue_id)
            if issue.status not in {
                OperationalIssueStatus.WAITING_EXTERNAL,
                OperationalIssueStatus.IMPLEMENTING,
            }:
                raise ValueError("Issue cannot accept implementation evidence")
            content = {
                "summary": summary,
                "branch": branch,
                "commits": commits,
                "validation": validation,
                "implemented_by": implemented_by,
            }
            self._add_artifact(
                session,
                issue,
                "implementation",
                content,
                implemented_by,
            )
            issue.improvement_branch = branch or issue.improvement_branch
            issue.status = OperationalIssueStatus.EVALUATING
            issue.evaluation_status = "queued"
            self._enqueue(
                session,
                issue,
                job_type="operational_evaluation",
                priority=self._priority(issue.severity),
            )
            self._append_event(
                session,
                issue,
                "issue.implementation.recorded",
                {"implemented_by": implemented_by, "branch": branch},
            )
            session.commit()
            session.refresh(issue)
            return issue

    def record_implementation_completed(self, task_id: str) -> None:
        with self._database.session_factory() as session:
            issue = session.scalar(
                select(OperationalIssue).where(
                    OperationalIssue.implementation_task_id == task_id
                )
            )
            if issue is None:
                return
            task = session.get(Task, task_id)
            if task is None:
                return
            self._add_artifact(
                session,
                issue,
                "implementation",
                {
                    "task_id": task.id,
                    "branch": issue.improvement_branch,
                    "workspace_path": task.workspace_path,
                    "workspace_commit": task.workspace_commit,
                    "report": task.final_report or {},
                },
                "cag-self-operations",
            )
            issue.status = OperationalIssueStatus.EVALUATING
            issue.evaluation_status = "queued"
            self._enqueue(
                session,
                issue,
                job_type="operational_evaluation",
                priority=self._priority(issue.severity),
            )
            self._append_event(
                session,
                issue,
                "issue.implementation.completed",
                {"task_id": task.id, "branch": issue.improvement_branch},
            )
            session.commit()

    def capture_queue_failure(self, item_id: str) -> OperationalIssue | None:
        with self._database.session_factory() as session:
            item = session.get(QueueItem, item_id)
            if item is None:
                return None
            if item.issue_id is not None:
                issue = session.get(OperationalIssue, item.issue_id)
                if issue is not None:
                    issue.status = OperationalIssueStatus.TRIAGE_FAILED
                    issue.summary = item.error or "Operational worker failed"
                    session.add(
                        OperationalIssueOccurrence(
                            issue_id=issue.id,
                            event_type="operations_worker_failure",
                            error_type="QueueWorkerError",
                            error_message=issue.summary,
                            evidence={"queue_item_id": item.id},
                        )
                    )
                    self._append_event(
                        session,
                        issue,
                        "issue.processing.failed",
                        {"queue_item_id": item.id, "error": item.error},
                    )
                    session.commit()
                    return issue
                return None
            if item.task_id is not None:
                task = session.get(Task, item.task_id)
                if task is None:
                    return None
                linked_issue_id = (task.request_metadata or {}).get(
                    "operational_issue_id"
                )
                if linked_issue_id:
                    issue = session.get(OperationalIssue, str(linked_issue_id))
                    if issue is not None:
                        issue.status = OperationalIssueStatus.DETECTED
                        issue.summary = task.error or "Improvement task failed"
                        session.add(
                            OperationalIssueOccurrence(
                                issue_id=issue.id,
                                event_type="implementation_failure",
                                error_type="TaskFailure",
                                error_message=issue.summary,
                                evidence={"task_id": task.id},
                            )
                        )
                        self._enqueue(
                            session,
                            issue,
                            job_type="operational_triage",
                            priority=self._priority(issue.severity),
                        )
                        self._append_event(
                            session,
                            issue,
                            "issue.implementation.failed",
                            {"task_id": task.id, "error": task.error},
                        )
                        session.commit()
                        return issue
                project_code = task.project.code
                payload = {
                    "project_reference": project_code,
                    "source_type": "task",
                    "source_id": task.id,
                    "title": f"Task failed: {task.id[:8]}",
                    "error_type": "TaskFailure",
                    "error_message": task.error or "Task failed",
                    "severity": "high",
                    "evidence": {
                        "task_id": task.id,
                        "runtime_profile": task.runtime_profile,
                        "trigger_source": task.trigger_source,
                    },
                }
            else:
                ingestion = session.get(KnowledgeIngestion, item.ingestion_id)
                if ingestion is None:
                    return None
                source = session.get(KnowledgeSource, ingestion.source_id)
                if source is None:
                    return None
                project = session.get(Project, source.project_id)
                if project is None:
                    return None
                payload = {
                    "project_reference": project.code,
                    "source_type": "knowledge_ingestion",
                    "source_id": ingestion.id,
                    "title": f"Knowledge ingestion failed: {source.name}",
                    "error_type": "KnowledgeIngestionFailure",
                    "error_message": ingestion.error or "Knowledge ingestion failed",
                    "severity": "high",
                    "evidence": {
                        "ingestion_id": ingestion.id,
                        "knowledge_source_id": source.id,
                        "knowledge_source_name": source.name,
                        "trigger": ingestion.trigger,
                    },
                }
        return self.capture(**payload)

    def record_manual_evaluation(
        self,
        issue_id: str,
        *,
        evaluated_by: str,
        passed: bool,
        summary: str,
        metrics: dict[str, Any],
    ) -> OperationalIssue:
        with self._database.session_factory() as session:
            issue = session.get(OperationalIssue, issue_id)
            if issue is None:
                raise KeyError(issue_id)
            self._add_artifact(
                session,
                issue,
                "evaluation",
                {
                    "passed": passed,
                    "summary": summary,
                    "metrics": metrics,
                },
                evaluated_by,
            )
            issue.evaluation_status = "passed" if passed else "failed"
            if passed:
                issue.status = OperationalIssueStatus.CLOSED
                issue.resolution = summary
                issue.closed_by = evaluated_by
                issue.closed_at = utc_now()
                event_type = "issue.closed"
            else:
                issue.status = OperationalIssueStatus.DETECTED
                issue.approval_status = "not_requested"
                self._enqueue(
                    session,
                    issue,
                    job_type="operational_triage",
                    priority=self._priority(issue.severity),
                )
                event_type = "issue.evaluation.failed"
            self._append_event(
                session,
                issue,
                event_type,
                {"passed": passed, "evaluated_by": evaluated_by},
            )
            session.commit()
            session.refresh(issue)
            return issue

    def reopen(
        self,
        issue_id: str,
        *,
        reopened_by: str,
        reason: str,
    ) -> OperationalIssue:
        with self._database.session_factory() as session:
            issue = session.get(OperationalIssue, issue_id)
            if issue is None:
                raise KeyError(issue_id)
            issue.status = OperationalIssueStatus.DETECTED
            issue.closed_at = None
            issue.closed_by = None
            issue.resolution = None
            issue.approval_status = "not_requested"
            issue.evaluation_status = "not_started"
            issue.review_recommendation = None
            issue.blocking_finding_count = 0
            issue.decision_brief = {}
            self._enqueue(
                session,
                issue,
                job_type="operational_triage",
                priority=self._priority(issue.severity),
            )
            self._append_event(
                session,
                issue,
                "issue.reopened",
                {"reopened_by": reopened_by, "reason": reason},
            )
            session.commit()
            session.refresh(issue)
            return issue

    def list_issues(
        self,
        *,
        status: str | None = None,
        severity: str | None = None,
        boundary: str | None = None,
        resolution_mode: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        statement = select(OperationalIssue).order_by(
            OperationalIssue.last_seen_at.desc()
        ).limit(limit)
        if status:
            statement = statement.where(OperationalIssue.status == status)
        if severity:
            statement = statement.where(OperationalIssue.severity == severity)
        if boundary:
            statement = statement.where(OperationalIssue.boundary == boundary)
        if resolution_mode:
            statement = statement.where(
                OperationalIssue.resolution_mode == resolution_mode
            )
        with self._database.session_factory() as session:
            return [
                self._issue_summary(issue)
                for issue in session.scalars(statement)
            ]

    def get_issue(self, issue_id: str) -> dict[str, Any]:
        with self._database.session_factory() as session:
            issue = session.get(OperationalIssue, issue_id)
            if issue is None:
                raise KeyError(issue_id)
            response = self._issue_summary(issue)
            response["occurrences"] = [
                self._occurrence_response(item)
                for item in session.scalars(
                    select(OperationalIssueOccurrence)
                    .where(OperationalIssueOccurrence.issue_id == issue.id)
                    .order_by(OperationalIssueOccurrence.occurred_at.desc())
                )
            ]
            response["artifacts"] = [
                self._artifact_response(item)
                for item in session.scalars(
                    select(OperationalIssueArtifact)
                    .where(OperationalIssueArtifact.issue_id == issue.id)
                    .order_by(
                        OperationalIssueArtifact.created_at,
                        OperationalIssueArtifact.revision,
                    )
                )
            ]
            response["events"] = [
                self._event_response(item)
                for item in session.scalars(
                    select(OperationalIssueEvent)
                    .where(OperationalIssueEvent.issue_id == issue.id)
                    .order_by(OperationalIssueEvent.sequence)
                )
            ]
            return response

    def dashboard(self) -> dict[str, Any]:
        with self._database.session_factory() as session:
            status_rows = session.execute(
                select(
                    OperationalIssue.status,
                    func.count(OperationalIssue.id),
                ).group_by(OperationalIssue.status)
            )
            severity_rows = session.execute(
                select(
                    OperationalIssue.severity,
                    func.count(OperationalIssue.id),
                ).group_by(OperationalIssue.severity)
            )
            boundary_rows = session.execute(
                select(
                    OperationalIssue.boundary,
                    func.count(OperationalIssue.id),
                ).group_by(OperationalIssue.boundary)
            )
            resolution_rows = session.execute(
                select(
                    OperationalIssue.resolution_mode,
                    func.count(OperationalIssue.id),
                ).group_by(OperationalIssue.resolution_mode)
            )
            return {
                "total": int(
                    session.scalar(select(func.count(OperationalIssue.id))) or 0
                ),
                "by_status": {str(key): int(value) for key, value in status_rows},
                "by_severity": {
                    str(key): int(value) for key, value in severity_rows
                },
                "by_boundary": {
                    str(key or "unclassified"): int(value)
                    for key, value in boundary_rows
                },
                "by_resolution_mode": {
                    str(key or "undetermined"): int(value)
                    for key, value in resolution_rows
                },
            }

    async def _run_ai(
        self,
        *,
        issue_id: str,
        phase: str,
        project_code: str,
        workspace_path,
        prompt: str,
    ) -> RuntimeResult:
        async def emit(event_type: str, data: dict[str, Any]) -> None:
            await asyncio.to_thread(
                self._record_runtime_event,
                issue_id,
                phase,
                event_type,
                data,
            )

        return await self._runtime.execute(
            task_id=f"{issue_id}:{phase}",
            project_code=project_code,
            prompt=prompt,
            runtime_profile="read-only-analysis",
            persistent_conversation=False,
            conversation_thread_id=None,
            workspace_path=workspace_path,
            additional_workspace_roots=(),
            developer_instructions=(
                "This operational planning and review phase is strictly read-only. "
                "Do not edit files, run destructive commands, create branches, commit, "
                "push, change services, or expose secrets. Return evidence-backed "
                "analysis through the structured runtime result."
            ),
            emit=emit,
            request_approval=None,
        )

    def _record_runtime_event(
        self,
        issue_id: str,
        phase: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        if event_type.endswith(".delta"):
            return
        with self._database.session_factory() as session:
            issue = session.get(OperationalIssue, issue_id)
            if issue is None:
                return
            self._append_event(
                session,
                issue,
                f"ai.{phase}.{event_type}",
                self._sanitize_value(data),
            )
            session.commit()

    def _enqueue(
        self,
        session,
        issue: OperationalIssue,
        *,
        job_type: str,
        priority: int,
    ) -> QueueItem:
        existing = session.scalar(
            select(QueueItem).where(
                QueueItem.issue_id == issue.id,
                QueueItem.job_type == job_type,
                QueueItem.status.in_(
                    (QueueItemStatus.QUEUED, QueueItemStatus.LEASED)
                ),
            )
        )
        if existing is not None:
            return existing
        item = QueueItem(
            queue_name="operations",
            job_type=job_type,
            issue_id=issue.id,
            project_id=issue.project_id,
            client_id="cag-self-operations",
            priority=priority,
            max_attempts=3,
        )
        session.add(item)
        session.flush()
        return item

    @staticmethod
    def _append_event(
        session,
        issue: OperationalIssue,
        event_type: str,
        data: dict[str, Any],
    ) -> OperationalIssueEvent:
        sequence = session.scalar(
            update(OperationalIssue)
            .where(OperationalIssue.id == issue.id)
            .values(
                event_sequence=OperationalIssue.event_sequence + 1,
            )
            .returning(OperationalIssue.event_sequence)
        )
        if sequence is None:
            raise RuntimeError("Operational issue event sequence is unavailable")
        issue.event_sequence = int(sequence)
        event = OperationalIssueEvent(
            issue_id=issue.id,
            sequence=int(sequence),
            type=event_type,
            data=data,
        )
        session.add(event)
        session.flush()
        return event

    @staticmethod
    def _add_artifact(
        session,
        issue: OperationalIssue,
        artifact_type: str,
        content: dict[str, Any],
        created_by: str,
    ) -> OperationalIssueArtifact:
        revision = int(
            session.scalar(
                select(func.max(OperationalIssueArtifact.revision)).where(
                    OperationalIssueArtifact.issue_id == issue.id,
                    OperationalIssueArtifact.artifact_type == artifact_type,
                )
            )
            or 0
        ) + 1
        artifact = OperationalIssueArtifact(
            issue_id=issue.id,
            artifact_type=artifact_type,
            revision=revision,
            content=content,
            created_by=created_by,
        )
        session.add(artifact)
        session.flush()
        return artifact

    @staticmethod
    def _latest_artifact_content(
        session,
        issue_id: str,
        artifact_type: str,
    ) -> dict[str, Any]:
        artifact = session.scalar(
            select(OperationalIssueArtifact)
            .where(
                OperationalIssueArtifact.issue_id == issue_id,
                OperationalIssueArtifact.artifact_type == artifact_type,
            )
            .order_by(OperationalIssueArtifact.revision.desc())
            .limit(1)
        )
        return artifact.content if artifact is not None else {}

    @staticmethod
    def _fingerprint(
        project_id: str,
        source_type: str,
        error_type: str | None,
        error_message: str,
    ) -> str:
        normalized = re.sub(
            r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b|\b\d{4,}\b",
            "{id}",
            error_message.lower(),
        )
        normalized = re.sub(r"\s+", " ", normalized).strip()[:1_000]
        return sha256(
            f"{project_id}|{source_type}|{error_type or ''}|{normalized}".encode(
                "utf-8"
            )
        ).hexdigest()

    @staticmethod
    def _priority(severity: str) -> int:
        return {
            "critical": 300,
            "high": 200,
            "medium": 100,
            "low": 50,
        }.get(severity, 100)

    @classmethod
    def _sanitize_text(cls, value: str) -> str:
        result = value
        for pattern in SECRET_PATTERNS:
            result = pattern.sub("[REDACTED]", result)
        return result

    @classmethod
    def _sanitize_value(cls, value: Any) -> Any:
        if isinstance(value, str):
            return cls._sanitize_text(value)
        if isinstance(value, dict):
            return {
                str(key): cls._sanitize_value(item)
                for key, item in value.items()
                if str(key).lower()
                not in {"password", "secret", "token", "api_key"}
            }
        if isinstance(value, list):
            return [cls._sanitize_value(item) for item in value]
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return str(value)

    @staticmethod
    def _parse_runtime_model(
        result: RuntimeResult,
        model_type: type[OperationsModel],
    ) -> OperationsModel:
        raw = result.summary.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw, count=1)
            raw = re.sub(r"\s*```\s*$", "", raw, count=1)
        decoder = json.JSONDecoder()
        candidates = [match.start() for match in re.finditer(r"\{", raw)]
        errors: list[str] = []
        for start in candidates:
            try:
                payload, _ = decoder.raw_decode(raw[start:])
                if not isinstance(payload, dict):
                    continue
                return model_type.model_validate(payload)
            except (json.JSONDecodeError, ValidationError) as exc:
                errors.append(str(exc))
        detail = errors[-1] if errors else "No JSON object was found"
        raise ValueError(
            f"{model_type.__name__} structured output is invalid: {detail}"
        )

    @staticmethod
    def _default_resolution_mode(boundary: str) -> str:
        if boundary == BOUNDARY_INTERNAL:
            return RESOLUTION_AGENT
        if boundary in {BOUNDARY_EXTERNAL, BOUNDARY_CREDENTIAL}:
            return RESOLUTION_EXTERNAL
        if boundary == BOUNDARY_SCOPE:
            return RESOLUTION_OUT_OF_SCOPE
        return RESOLUTION_UNDETERMINED

    @staticmethod
    def _reconcile_resolution_mode(
        boundary: str,
        proposed_mode: str,
    ) -> str:
        if boundary == BOUNDARY_SCOPE:
            return RESOLUTION_OUT_OF_SCOPE
        if boundary in {BOUNDARY_EXTERNAL, BOUNDARY_CREDENTIAL}:
            if proposed_mode == RESOLUTION_MIXED:
                return RESOLUTION_MIXED
            return RESOLUTION_EXTERNAL
        if boundary == BOUNDARY_INTERNAL and proposed_mode in {
            RESOLUTION_AGENT,
            RESOLUTION_HUMAN_CODE,
            RESOLUTION_MIXED,
            RESOLUTION_UNDETERMINED,
        }:
            return proposed_mode
        return RESOLUTION_UNDETERMINED

    @staticmethod
    def _required_human_input(
        *,
        boundary: str,
        resolution_mode: str,
        administrator_actions: list[str],
    ) -> str | None:
        if resolution_mode == RESOLUTION_AGENT:
            default = (
                "Administrator approval is required before Agent "
                "self-improvement starts."
            )
        elif resolution_mode == RESOLUTION_HUMAN_CODE:
            default = (
                "A human engineer must implement or supervise the required "
                "code change."
            )
        elif resolution_mode == RESOLUTION_EXTERNAL:
            default = (
                "An authorized operator or external owner must complete the "
                "required action."
            )
        elif resolution_mode == RESOLUTION_MIXED:
            default = (
                "Agent implementation and an authorized human or external "
                "action are both required."
            )
        elif boundary == BOUNDARY_SCOPE:
            default = "A responsible owner must accept the handoff."
        else:
            default = "More evidence is required before selecting an execution route."
        actions = [item.strip() for item in administrator_actions if item.strip()]
        return " ".join([default, *actions])[:8_000]

    @staticmethod
    def _actions_for_resolution(
        boundary: str,
        resolution_mode: str,
    ) -> list[str]:
        if boundary == BOUNDARY_SCOPE:
            return ["document_handoff"]
        if resolution_mode == RESOLUTION_AGENT:
            return [
                "plan",
                "review",
                "request_approval",
                "implement_in_isolated_branch",
                "evaluate",
                "rollback",
            ]
        if resolution_mode == RESOLUTION_HUMAN_CODE:
            return [
                "plan",
                "review",
                "request_approval",
                "record_manual_implementation",
                "evaluate",
            ]
        if resolution_mode == RESOLUTION_EXTERNAL:
            return [
                "diagnose",
                "request_approval",
                "retry_after_authorization",
                "record_external_fix",
            ]
        if resolution_mode == RESOLUTION_MIXED:
            return [
                "plan",
                "review",
                "request_approval",
                "implement_in_isolated_branch",
                "record_external_fix",
                "evaluate",
                "rollback",
            ]
        return ["diagnose", "request_more_evidence", "replan"]

    @staticmethod
    def _merge_string_lists(*groups: list[Any]) -> list[str]:
        result: list[str] = []
        for group in groups:
            for value in group:
                normalized = (
                    value.strip()
                    if isinstance(value, str)
                    else json.dumps(value, ensure_ascii=False, sort_keys=True)
                )
                if normalized and normalized not in result:
                    result.append(normalized)
        return result

    @staticmethod
    def _classify(
        evidence: dict[str, Any],
        analysis: RuntimeResult,
    ) -> tuple[str, float, str | None, list[str]]:
        text = " ".join(
            (
                str(evidence.get("source_type", "")),
                str(evidence.get("title", "")),
                str(evidence.get("summary", "")),
                str(analysis.root_cause or ""),
            )
        ).lower()
        if any(
            marker in text
            for marker in (
                "authentication",
                "credential",
                "unauthorized",
                "permission denied",
                "access denied",
                "errno 86",
                "认证",
                "凭据",
                "授权",
            )
        ):
            return (
                BOUNDARY_CREDENTIAL,
                0.96,
                "Administrator credential or authorization action is required.",
                ["diagnose", "retry_after_authorization", "record_external_fix"],
            )
        if any(
            marker in text
            for marker in (
                "network",
                "connection refused",
                "timeout",
                "redis",
                "postgres",
                "ollama",
                "unavailable",
                "网络",
                "连接",
            )
        ):
            return (
                BOUNDARY_EXTERNAL,
                0.88,
                "Administrator confirmation of external service recovery is required.",
                ["diagnose", "retry", "record_external_fix"],
            )
        if any(
            marker in text
            for marker in ("out_of_scope", "policy_scope", "legal_boundary")
        ):
            return (
                BOUNDARY_SCOPE,
                0.95,
                "A responsible external owner must accept the handoff.",
                ["document_handoff"],
            )
        return (
            BOUNDARY_INTERNAL,
            0.84,
            None,
            [
                "plan",
                "review",
                "request_approval",
                "implement_in_isolated_branch",
                "evaluate",
                "rollback",
            ],
        )

    @staticmethod
    def _default_acceptance(evidence: dict[str, Any]) -> list[str]:
        acceptance = [
            "Replay the original failure and verify the expected result.",
            "Run targeted regression, security, and rollback checks.",
            "Keep the Gateway health endpoint responsive throughout validation.",
            "Preserve immutable issue, approval, implementation, and evaluation evidence.",
        ]
        if evidence.get("source_type") in {"api", "knowledge_search"}:
            acceptance.append(
                "Verify bounded latency and memory on the production-sized corpus."
            )
        return acceptance

    @staticmethod
    def _issue_summary(issue: OperationalIssue) -> dict[str, Any]:
        return {
            "id": issue.id,
            "project_id": issue.project_id,
            "parent_issue_id": issue.parent_issue_id,
            "implementation_task_id": issue.implementation_task_id,
            "code": issue.code,
            "fingerprint": issue.fingerprint,
            "source_type": issue.source_type,
            "source_id": issue.source_id,
            "title": issue.title,
            "summary": issue.summary,
            "severity": issue.severity,
            "boundary": issue.boundary,
            "boundary_confidence": issue.boundary_confidence,
            "resolution_mode": issue.resolution_mode,
            "resolution_mode_confidence": issue.resolution_mode_confidence,
            "resolution_mode_reason": issue.resolution_mode_reason,
            "decision_brief": issue.decision_brief or {},
            "review_recommendation": issue.review_recommendation,
            "blocking_finding_count": issue.blocking_finding_count,
            "status": issue.status,
            "occurrence_count": issue.occurrence_count,
            "evidence": issue.evidence,
            "allowed_actions": issue.allowed_actions,
            "required_human_input": issue.required_human_input,
            "approval_status": issue.approval_status,
            "approved_by": issue.approved_by,
            "approval_note": issue.approval_note,
            "approved_at": (
                issue.approved_at.isoformat() if issue.approved_at else None
            ),
            "improvement_branch": issue.improvement_branch,
            "evaluation_status": issue.evaluation_status,
            "resolution": issue.resolution,
            "closed_by": issue.closed_by,
            "first_seen_at": issue.first_seen_at.isoformat(),
            "last_seen_at": issue.last_seen_at.isoformat(),
            "created_at": issue.created_at.isoformat(),
            "updated_at": issue.updated_at.isoformat(),
            "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
        }

    @staticmethod
    def _occurrence_response(item: OperationalIssueOccurrence) -> dict[str, Any]:
        return {
            "id": item.id,
            "external_event_id": item.external_event_id,
            "event_type": item.event_type,
            "error_type": item.error_type,
            "error_message": item.error_message,
            "evidence": item.evidence,
            "occurred_at": item.occurred_at.isoformat(),
        }

    @staticmethod
    def _artifact_response(item: OperationalIssueArtifact) -> dict[str, Any]:
        return {
            "id": item.id,
            "artifact_type": item.artifact_type,
            "revision": item.revision,
            "content": item.content,
            "created_by": item.created_by,
            "created_at": item.created_at.isoformat(),
        }

    @staticmethod
    def _event_response(item: OperationalIssueEvent) -> dict[str, Any]:
        return {
            "id": item.id,
            "sequence": item.sequence,
            "type": item.type,
            "data": item.data,
            "created_at": item.created_at.isoformat(),
        }
