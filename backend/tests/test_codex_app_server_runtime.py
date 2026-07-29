import asyncio
from pathlib import Path
import sys

import pytest

from app.runtimes.codex_app_server import (
    CodexAppServerError,
    CodexAppServerRuntime,
)


FIXTURE_SERVER = Path(__file__).parent / "fixtures" / "fake_app_server.py"


def execute_runtime(
    tmp_path: Path,
    *,
    account_type: str = "chatgpt",
    mode: str = "normal",
    persistent_conversation: bool = True,
    conversation_thread_id: str | None = None,
    developer_instructions: str | None = None,
) -> tuple[object, list[tuple[str, dict[str, object]]]]:
    command = [sys.executable, str(FIXTURE_SERVER), account_type]
    command.append(mode)
    runtime = CodexAppServerRuntime(
        command=command,
        startup_timeout_seconds=5,
        turn_timeout_seconds=5,
    )
    events: list[tuple[str, dict[str, object]]] = []

    async def emit(event_type: str, data: dict[str, object]) -> None:
        events.append((event_type, data))

    result = asyncio.run(
        runtime.execute(
            task_id="task-1",
            project_code="cag",
            prompt="inspect",
            runtime_profile="read-only-analysis",
            persistent_conversation=persistent_conversation,
            conversation_thread_id=conversation_thread_id,
            workspace_path=tmp_path,
            additional_workspace_roots=(),
            developer_instructions=developer_instructions,
            emit=emit,
        )
    )
    return result, events


def test_codex_app_server_maps_protocol_to_gateway_events(
    tmp_path: Path,
) -> None:
    result, events = execute_runtime(tmp_path)

    assert result.summary == "LOCAL_CODEX_FIXTURE_OK"
    assert result.validation == [
        {
            "command": "git status --short",
            "status": "completed",
            "exit_code": 0,
        }
    ]
    assert result.changes == [
        {
            "status": "completed",
            "changes": [{"path": "README.md", "kind": "update"}],
        }
    ]
    assert result.warnings == [
        "fixture warning",
        "{'message': 'recoverable fixture error'}",
    ]
    assert [event_type for event_type, _ in events] == [
        "runtime.connected",
        "runtime.thread",
        "agent.plan.delta",
        "agent.plan",
        "command.started",
        "command.output.delta",
        "command.completed",
        "file.changed",
        "agent.message",
        "agent.reasoning.summary.delta",
        "agent.message.started",
        "agent.message.delta",
        "agent.message.delta",
        "agent.message",
    ]
    assert events[0][1]["authentication"] == "chatgpt"
    assert events[1][1] == {
        "thread_id": "thread-1",
        "action": "started",
    }
    assert events[2][1] == {
        "item_id": "item-plan",
        "turn_id": "turn-1",
        "delta": "inspect",
    }
    assert events[5][1] == {
        "item_id": "item-command",
        "turn_id": "turn-1",
        "delta": "clean workspace\n",
    }
    assert events[9][1] == {
        "item_id": "item-reasoning",
        "turn_id": "turn-1",
        "summary_index": 0,
        "delta": "fixture summary",
    }
    assert events[11][1] == {
        "item_id": "item-message",
        "turn_id": "turn-1",
        "delta": "LOCAL_CODEX_",
        "text": "LOCAL_CODEX_",
    }
    assert events[12][1] == {
        "item_id": "item-message",
        "turn_id": "turn-1",
        "delta": "FIXTURE_OK",
        "text": "LOCAL_CODEX_FIXTURE_OK",
    }
    assert events[13][1] == {
        "item_id": "item-message",
        "turn_id": "turn-1",
        "text": "LOCAL_CODEX_FIXTURE_OK",
    }


def test_codex_app_server_resumes_persisted_thread(tmp_path: Path) -> None:
    result, events = execute_runtime(
        tmp_path,
        conversation_thread_id="thread-existing",
    )

    assert result.runtime_thread_id == "thread-existing"
    assert events[1][1] == {
        "thread_id": "thread-existing",
        "action": "resumed",
    }


def test_codex_app_server_receives_resource_linked_knowledge(
    tmp_path: Path,
) -> None:
    result, _ = execute_runtime(
        tmp_path,
        mode="expect-knowledge-context",
        developer_instructions=(
            '<knowledge resource_uri="file:///D:/knowledge/runbook.md">'
            "verified evidence</knowledge>"
        ),
    )

    assert result.summary == "LOCAL_CODEX_FIXTURE_OK"


def test_codex_app_server_uses_ephemeral_thread_without_conversation(
    tmp_path: Path,
) -> None:
    result, _ = execute_runtime(
        tmp_path,
        mode="expect-ephemeral",
        persistent_conversation=False,
    )

    assert result.summary == "LOCAL_CODEX_FIXTURE_OK"


def test_codex_app_server_declines_approval_until_phase5(
    tmp_path: Path,
) -> None:
    result, events = execute_runtime(tmp_path, mode="approval")

    assert result.approvals == [
        {
            "method": "item/commandExecution/requestApproval",
            "decision": "decline",
        }
    ]
    assert "approval.requested" in [event_type for event_type, _ in events]
    assert "approval.resolved" in [event_type for event_type, _ in events]


def test_codex_app_server_rejects_api_key_authentication(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        CodexAppServerError,
        match="authenticated through ChatGPT",
    ):
        execute_runtime(tmp_path, account_type="apiKey")


def test_codex_app_server_handles_non_approval_server_requests(
    tmp_path: Path,
) -> None:
    result, _ = execute_runtime(tmp_path, mode="requests")

    assert result.summary == "LOCAL_CODEX_FIXTURE_OK"


def test_codex_app_server_rejects_invalid_json(tmp_path: Path) -> None:
    with pytest.raises(CodexAppServerError, match="invalid JSONL"):
        execute_runtime(tmp_path, mode="invalid-json")
