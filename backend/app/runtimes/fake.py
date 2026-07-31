import asyncio
import json
from pathlib import Path

from app.runtimes.base import RuntimeEventCallback, RuntimeResult


class FakeAgentRuntime:
    def __init__(self, delay_ms: int = 0) -> None:
        self._delay_seconds = delay_ms / 1000

    async def _pause(self) -> None:
        if self._delay_seconds:
            await asyncio.sleep(self._delay_seconds)

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
        request_approval=None,
    ) -> RuntimeResult:
        await emit(
            "agent.plan",
            {
                "steps": [
                    "inspect_project",
                    "analyze_prompt",
                    "produce_report",
                ],
                "runtime": "fake",
                "workspace_ready": workspace_path.is_dir(),
            },
        )
        await self._pause()
        await emit(
            "agent.message",
            {
                "text": (
                    f"Fake runtime accepted task {task_id} for project "
                    f"{project_code} with profile {runtime_profile}."
                )
            },
        )
        await self._pause()
        await emit(
            "test.completed",
            {
                "command": "fake-runtime-validation",
                "status": "passed",
            },
        )
        await self._pause()

        summary = "Fake Agent Runtime completed the task deterministically."
        if '"blocking_findings"' in prompt:
            summary = json.dumps(
                {
                    "summary": (
                        "The bounded plan is ready for administrator review."
                    ),
                    "root_cause_assessment": (
                        "The plan is consistent with the supplied evidence."
                    ),
                    "recommendation": "approve",
                    "blocking_findings": [],
                    "approval_conditions": [
                        "Administrator approves the selected execution route."
                    ],
                    "validation_plan": [
                        "Run the deterministic regression validation."
                    ],
                    "warnings": [
                        "This review was produced by FakeAgentRuntime."
                    ],
                }
            )
        elif '"resolution_mode_reason"' in prompt:
            folded = prompt.rsplit("Issue evidence:", 1)[-1].casefold()
            if any(
                marker in folded
                for marker in (
                    "credential",
                    "authentication",
                    "password",
                    "errno 86",
                )
            ):
                boundary = "credential_or_authorization"
                resolution_mode = "external_operator_action"
            elif any(
                marker in folded
                for marker in (
                    "external dependency",
                    "connection timeout",
                    "network connection",
                )
            ):
                boundary = "external_dependency"
                resolution_mode = "external_operator_action"
            else:
                boundary = "cag_internal"
                resolution_mode = "agent_self_improvement"
            summary = json.dumps(
                {
                    "problem_summary": (
                        "The operational failure requires a bounded correction."
                    ),
                    "impact_summary": (
                        "The affected workflow is unavailable until recovery."
                    ),
                    "root_cause_summary": (
                        "Deterministic fake analysis identified the failure path."
                    ),
                    "root_cause_confidence": 0.9,
                    "improvement_goal": (
                        "Resolve the failure and prevent recurrence."
                    ),
                    "resolution_mode": resolution_mode,
                    "resolution_mode_reason": (
                        "The selected route follows the verified responsibility "
                        "boundary."
                    ),
                    "resolution_mode_confidence": 0.9,
                    "proposed_changes": [
                        {
                            "area": "failure path",
                            "change": "Apply the bounded corrective change.",
                            "reason": "The original failure must stop recurring.",
                        }
                    ],
                    "validation_plan": [
                        "Replay the original failure and verify recovery."
                    ],
                    "rollback_plan": [
                        "Restore the previous verified implementation."
                    ],
                    "administrator_actions": [
                        "Approve or reject the proposed execution route."
                    ],
                    "boundary": boundary,
                    "boundary_confidence": 0.9,
                }
            )
        return RuntimeResult(
            summary=summary,
            root_cause=None,
            changes=[],
            validation=[
                {
                    "command": "fake-runtime-validation",
                    "status": "passed",
                }
            ],
            approvals=[],
            warnings=[
                "This result was produced by FakeAgentRuntime.",
                f"Prompt length was {len(prompt)} characters.",
            ],
            next_actions=[
                "Run with the local Codex runtime after Phase 3 is enabled."
            ],
            runtime_thread_id=conversation_thread_id,
        )
