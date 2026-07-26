from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol


RuntimeEventCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class RuntimeResult:
    summary: str
    root_cause: str | None
    changes: list[dict[str, Any]]
    validation: list[dict[str, Any]]
    approvals: list[dict[str, Any]]
    warnings: list[str]
    next_actions: list[str]

    def to_report(self) -> dict[str, Any]:
        return {
            "status": "completed",
            "summary": self.summary,
            "root_cause": self.root_cause,
            "changes": self.changes,
            "validation": self.validation,
            "approvals": self.approvals,
            "warnings": self.warnings,
            "next_actions": self.next_actions,
        }


class AgentRuntime(Protocol):
    async def execute(
        self,
        *,
        task_id: str,
        project_code: str,
        prompt: str,
        runtime_profile: str,
        emit: RuntimeEventCallback,
    ) -> RuntimeResult: ...
