import asyncio
from collections.abc import Awaitable, Callable

from sqlalchemy import select

from app.database import Database
from app.models import ApprovalRequest, TaskStatus
from app.models.base import utc_now
from app.policies.command_policy import CommandPolicyService
from app.services.task_service import TaskService


class ApprovalService:
    def __init__(
        self,
        *,
        database: Database,
        task_service: TaskService,
        policy: CommandPolicyService,
        timeout_seconds: int,
        poll_interval_seconds: float = 0.25,
    ) -> None:
        self._database = database
        self._task_service = task_service
        self._policy = policy
        self._timeout_seconds = timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds

    async def request(
        self,
        *,
        task_id: str,
        agent_run_id: str | None,
        request_type: str,
        subject: str,
        on_pending: Callable[[dict[str, str]], Awaitable[None]] | None = None,
        access_mode: str = "workspace_write",
    ) -> tuple[str, str]:
        policy = self._policy.evaluate(subject, request_type)
        if access_mode == "read_only" and policy.decision == "approval_required":
            policy = type(policy)(
                decision="allow",
                risk_level="low",
                reason="Read-only Harness sandbox constrains the command",
            )
        initial_status = (
            "approved"
            if policy.decision == "allow"
            else "denied"
            if policy.decision == "deny"
            else "pending"
        )
        with self._database.session_factory() as session:
            approval = ApprovalRequest(
                task_id=task_id,
                agent_run_id=agent_run_id,
                request_type=request_type,
                subject=subject,
                risk_level=policy.risk_level,
                status=initial_status,
                policy_decision=policy.decision,
                resolved_at=utc_now() if initial_status != "pending" else None,
                resolved_by="command-policy" if initial_status != "pending" else None,
                resolution_note=policy.reason,
            )
            session.add(approval)
            if initial_status == "pending":
                task = self._task_service.get_task(session, task_id)
                task.status = TaskStatus.WAITING_APPROVAL
            session.commit()
            approval_id = approval.id
        if initial_status != "pending":
            return ("accept" if initial_status == "approved" else "decline", approval_id)
        if on_pending is not None:
            await on_pending(
                {
                    "approval_id": approval_id,
                    "request_type": request_type,
                    "subject": subject,
                    "risk_level": policy.risk_level,
                    "policy_decision": policy.decision,
                }
            )

        deadline = asyncio.get_running_loop().time() + self._timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(self._poll_interval_seconds)
            with self._database.session_factory() as session:
                approval = session.get(ApprovalRequest, approval_id)
                if approval is not None and approval.status in {"approved", "denied"}:
                    task = self._task_service.get_task(session, task_id)
                    task.status = TaskStatus.RUNNING
                    session.commit()
                    return (
                        "accept" if approval.status == "approved" else "decline",
                        approval_id,
                    )
        self.resolve(
            approval_id,
            decision="deny",
            resolved_by="gateway-timeout",
            note="Approval window expired",
        )
        return "decline", approval_id

    def resolve(
        self,
        approval_id: str,
        *,
        decision: str,
        resolved_by: str,
        note: str | None,
    ) -> ApprovalRequest:
        with self._database.session_factory() as session:
            approval = session.get(ApprovalRequest, approval_id)
            if approval is None:
                raise KeyError(approval_id)
            if approval.status != "pending":
                raise ValueError("Approval request is already resolved")
            approval.status = "approved" if decision == "approve" else "denied"
            approval.resolved_at = utc_now()
            approval.resolved_by = resolved_by
            approval.resolution_note = note
            session.commit()
            session.refresh(approval)
            session.expunge(approval)
            return approval

    def list_for_task(self, task_id: str) -> list[ApprovalRequest]:
        with self._database.session_factory() as session:
            approvals = list(
                session.scalars(
                    select(ApprovalRequest)
                    .where(ApprovalRequest.task_id == task_id)
                    .order_by(ApprovalRequest.requested_at)
                )
            )
            for approval in approvals:
                session.expunge(approval)
            return approvals
