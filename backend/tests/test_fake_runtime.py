import asyncio
from pathlib import Path

from app.runtimes.fake import FakeAgentRuntime


def test_fake_runtime_emits_deterministic_events(tmp_path: Path) -> None:
    emitted: list[tuple[str, dict[str, object]]] = []

    async def emit(event_type: str, data: dict[str, object]) -> None:
        emitted.append((event_type, data))

    result = asyncio.run(
        FakeAgentRuntime().execute(
            task_id="task-id",
            project_code="project-code",
            prompt="run tests",
            runtime_profile="general-engineering",
            workspace_path=tmp_path,
            emit=emit,
        )
    )

    assert [item[0] for item in emitted] == [
        "agent.plan",
        "agent.message",
        "test.completed",
    ]
    assert result.to_report()["status"] == "completed"
    assert result.validation == [
        {"command": "fake-runtime-validation", "status": "passed"}
    ]
    assert emitted[0][1]["workspace_ready"] is True
