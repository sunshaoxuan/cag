import asyncio
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

        return RuntimeResult(
            summary="Fake Agent Runtime completed the task deterministically.",
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
