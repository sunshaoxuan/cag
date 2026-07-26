import asyncio

from app.runtimes.fake import FakeAgentRuntime


def test_fake_runtime_emits_deterministic_events() -> None:
    emitted: list[tuple[str, dict[str, object]]] = []

    async def emit(event_type: str, data: dict[str, object]) -> None:
        emitted.append((event_type, data))

    result = asyncio.run(
        FakeAgentRuntime().execute(
            task_id="task-id",
            project_code="project-code",
            prompt="run tests",
            runtime_profile="general-engineering",
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
