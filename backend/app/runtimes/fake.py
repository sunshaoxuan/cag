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
                    "administrator_language": "zh-CN",
                    "summary": "该方案边界明确，可以提交管理员审核。",
                    "root_cause_assessment": (
                        "方案中的根因判断与现有证据一致。"
                    ),
                    "recommendation": "approve",
                    "blocking_findings": [],
                    "approval_conditions": [
                        "管理员确认并批准所选实施路线。"
                    ],
                    "validation_plan": [
                        "执行确定性的回归验证。"
                    ],
                    "warnings": [
                        "本 Review 由 FakeAgentRuntime 生成。"
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
                    "administrator_language": "zh-CN",
                    "problem_summary": "该运行故障需要有边界的修正。",
                    "impact_summary": "恢复完成前，受影响的流程不可用。",
                    "root_cause_summary": "确定性测试分析已识别故障路径。",
                    "root_cause_confidence": 0.9,
                    "improvement_goal": "解决当前故障并防止再次发生。",
                    "resolution_mode": resolution_mode,
                    "resolution_mode_reason": (
                        "所选实施路线与已经验证的责任边界一致。"
                    ),
                    "resolution_mode_confidence": 0.9,
                    "proposed_changes": [
                        {
                            "area": "故障路径",
                            "change": "实施有边界的修正。",
                            "reason": "需要阻止原始故障再次发生。",
                        }
                    ],
                    "validation_plan": [
                        "重放原始故障并验证恢复结果。"
                    ],
                    "rollback_plan": [
                        "恢复到上一版经过验证的实现。"
                    ],
                    "administrator_actions": [
                        "批准或拒绝建议的实施路线。"
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
