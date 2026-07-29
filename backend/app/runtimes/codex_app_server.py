import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.config import APP_VERSION
from app.runtimes.base import RuntimeApprovalCallback, RuntimeEventCallback, RuntimeResult


class CodexAppServerError(RuntimeError):
    pass


class CodexAppServerRuntime:
    def __init__(
        self,
        *,
        command: Sequence[str],
        startup_timeout_seconds: int = 30,
        turn_timeout_seconds: int = 900,
        require_chatgpt_auth: bool = True,
    ) -> None:
        if not command:
            raise ValueError("Codex app-server command cannot be empty")
        self._command = tuple(command)
        self._startup_timeout_seconds = startup_timeout_seconds
        self._turn_timeout_seconds = turn_timeout_seconds
        self._require_chatgpt_auth = require_chatgpt_auth

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
        request_approval: RuntimeApprovalCallback | None = None,
    ) -> RuntimeResult:
        process = await asyncio.create_subprocess_exec(
            *self._command,
            cwd=workspace_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        if process.stdin is None or process.stdout is None:
            process.kill()
            await process.wait()
            raise CodexAppServerError("Codex app-server stdio is unavailable")

        commands: list[dict[str, Any]] = []
        changes: list[dict[str, Any]] = []
        approvals: list[dict[str, Any]] = []
        warnings: list[str] = []
        final_message = ""
        message_text_by_item: dict[str, str] = {}
        next_request_id = 1

        async def send(message: dict[str, Any]) -> None:
            process.stdin.write(
                (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
            )
            await process.stdin.drain()

        async def read_message(timeout: int) -> dict[str, Any]:
            try:
                line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=timeout,
                )
            except TimeoutError as exc:
                raise CodexAppServerError(
                    "Codex app-server response timed out"
                ) from exc
            if not line:
                raise CodexAppServerError(
                    "Codex app-server exited before completion"
                )
            try:
                return json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise CodexAppServerError(
                    "Codex app-server returned invalid JSONL"
                ) from exc

        async def handle_server_request(message: dict[str, Any]) -> None:
            method = str(message.get("method", ""))
            request_id = message["id"]
            if method in {
                "item/commandExecution/requestApproval",
                "item/fileChange/requestApproval",
                "applyPatchApproval",
                "execCommandApproval",
            }:
                request_type = (
                    "file_change"
                    if "fileChange" in method or "applyPatch" in method
                    else "command"
                )
                params = message.get("params") or {}
                subject = str(
                    params.get("command")
                    or params.get("reason")
                    or params.get("changes")
                    or method
                )
                if request_approval is None:
                    decision, approval_id = "decline", None
                else:
                    decision, approval_id = await request_approval(
                        request_type, subject
                    )
                approval_record = {"method": method, "decision": decision}
                if approval_id is not None:
                    approval_record["approval_id"] = approval_id
                approvals.append(approval_record)
                await emit(
                    "approval.requested",
                    {
                        "method": method,
                        "subject": subject,
                        "approval_id": approval_id,
                    },
                )
                await send({"id": request_id, "result": {"decision": decision}})
                await emit(
                    "approval.resolved",
                    {
                        "method": method,
                        "decision": decision,
                        "approval_id": approval_id,
                    },
                )
                return
            if method == "item/tool/requestUserInput":
                await send({"id": request_id, "result": {"answers": {}}})
                return
            if method == "item/permissions/requestApproval":
                await send({"id": request_id, "result": {"permissions": {}}})
                return
            await send(
                {
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": "Gateway does not implement this server request",
                    },
                }
            )

        async def request(
            method: str,
            params: dict[str, Any],
            *,
            timeout: int,
        ) -> dict[str, Any]:
            nonlocal next_request_id
            request_id = next_request_id
            next_request_id += 1
            await send({"id": request_id, "method": method, "params": params})
            while True:
                message = await read_message(timeout)
                if "id" in message and "method" in message:
                    await handle_server_request(message)
                    continue
                if message.get("id") != request_id:
                    continue
                if "error" in message:
                    error = message["error"]
                    raise CodexAppServerError(
                        f"{method} failed: {error.get('message', error)}"
                    )
                result = message.get("result")
                if not isinstance(result, dict):
                    raise CodexAppServerError(
                        f"{method} returned an invalid result"
                    )
                return result

        async def handle_notification(message: dict[str, Any]) -> bool:
            nonlocal final_message
            method = message.get("method")
            params = message.get("params") or {}
            if method == "turn/plan/updated":
                await emit(
                    "agent.plan",
                    {
                        "steps": params.get("plan", []),
                        "explanation": params.get("explanation"),
                        "runtime": "codex-app-server",
                    },
                )
            elif method == "item/plan/delta":
                await emit(
                    "agent.plan.delta",
                    {
                        "item_id": str(params.get("itemId", "")),
                        "turn_id": str(params.get("turnId", "")),
                        "delta": str(params.get("delta", "")),
                    },
                )
            elif method == "item/agentMessage/delta":
                item_id = str(params.get("itemId", ""))
                delta = str(params.get("delta", ""))
                message_text = message_text_by_item.get(item_id, "") + delta
                message_text_by_item[item_id] = message_text
                final_message = message_text
                await emit(
                    "agent.message.delta",
                    {
                        "item_id": item_id,
                        "turn_id": str(params.get("turnId", "")),
                        "delta": delta,
                        "text": message_text,
                    },
                )
            elif method == "item/commandExecution/outputDelta":
                await emit(
                    "command.output.delta",
                    {
                        "item_id": str(params.get("itemId", "")),
                        "turn_id": str(params.get("turnId", "")),
                        "delta": str(params.get("delta", "")),
                    },
                )
            elif method == "item/reasoning/summaryTextDelta":
                await emit(
                    "agent.reasoning.summary.delta",
                    {
                        "item_id": str(params.get("itemId", "")),
                        "turn_id": str(params.get("turnId", "")),
                        "summary_index": params.get("summaryIndex"),
                        "delta": str(params.get("delta", "")),
                    },
                )
            elif method == "item/started":
                item = params.get("item") or {}
                item_type = item.get("type")
                if item_type == "agentMessage":
                    item_id = str(item.get("id", ""))
                    message_text_by_item[item_id] = str(item.get("text", ""))
                    await emit(
                        "agent.message.started",
                        {
                            "item_id": item_id,
                            "turn_id": str(params.get("turnId", "")),
                        },
                    )
                elif item_type == "commandExecution":
                    await emit(
                        "command.started",
                        {
                            "item_id": str(item.get("id", "")),
                            "turn_id": str(params.get("turnId", "")),
                            "command": item.get("command", ""),
                        },
                    )
            elif method == "item/completed":
                item = params.get("item") or {}
                item_type = item.get("type")
                if item_type == "agentMessage":
                    item_id = str(item.get("id", ""))
                    final_message = str(
                        item.get("text")
                        or message_text_by_item.get(item_id)
                        or final_message
                    )
                    await emit(
                        "agent.message",
                        {
                            "item_id": item_id,
                            "turn_id": str(params.get("turnId", "")),
                            "text": final_message,
                        },
                    )
                    message_text_by_item.pop(item_id, None)
                elif item_type == "commandExecution":
                    command_result = {
                        "command": item.get("command", ""),
                        "status": item.get("status", "unknown"),
                        "exit_code": item.get("exitCode"),
                    }
                    commands.append(command_result)
                    await emit(
                        "command.completed",
                        {
                            "item_id": str(item.get("id", "")),
                            "turn_id": str(params.get("turnId", "")),
                            **command_result,
                        },
                    )
                elif item_type == "fileChange":
                    change_result = {
                        "status": item.get("status", "unknown"),
                        "changes": item.get("changes", []),
                    }
                    changes.append(change_result)
                    await emit("file.changed", change_result)
            elif method == "warning":
                warning = str(params.get("message", "Codex warning"))
                warnings.append(warning)
                await emit("agent.message", {"text": warning, "level": "warning"})
            elif method == "error":
                error = params.get("error") or params
                warnings.append(str(error))
            elif method == "turn/completed":
                turn = params.get("turn") or {}
                status = turn.get("status")
                if status != "completed":
                    error = turn.get("error") or {}
                    raise CodexAppServerError(
                        str(error.get("message") or f"Codex turn {status}")
                    )
                return True
            return False

        try:
            await request(
                "initialize",
                {
                    "clientInfo": {
                        "name": "agent-gateway",
                        "title": "One Agent Gateway",
                        "version": APP_VERSION,
                    },
                    "capabilities": {"experimentalApi": True},
                },
                timeout=self._startup_timeout_seconds,
            )
            await send({"method": "initialized"})

            account_result = await request(
                "account/read",
                {"refreshToken": False},
                timeout=self._startup_timeout_seconds,
            )
            account = account_result.get("account") or {}
            account_type = account.get("type")
            if self._require_chatgpt_auth and account_type != "chatgpt":
                raise CodexAppServerError(
                    "Local Codex must be authenticated through ChatGPT"
                )
            await emit(
                "runtime.connected",
                {
                    "provider": "local-codex-app-server",
                    "authentication": account_type,
                },
            )

            sandbox = (
                "read-only"
                if runtime_profile == "read-only-analysis"
                else "workspace-write"
            )
            runtime_workspace_roots = [
                str(workspace_path),
                *(str(path) for path in additional_workspace_roots),
            ]
            if conversation_thread_id is None:
                thread_method = "thread/start"
                thread_params = {
                    "cwd": str(workspace_path),
                    "runtimeWorkspaceRoots": runtime_workspace_roots,
                    "sandbox": sandbox,
                    "approvalPolicy": "untrusted" if request_approval else "never",
                    "ephemeral": not persistent_conversation,
                    "serviceName": f"agent-gateway:{project_code}",
                    "developerInstructions": developer_instructions,
                }
            else:
                thread_method = "thread/resume"
                thread_params = {
                    "threadId": conversation_thread_id,
                    "cwd": str(workspace_path),
                    "runtimeWorkspaceRoots": runtime_workspace_roots,
                    "sandbox": sandbox,
                    "approvalPolicy": "untrusted" if request_approval else "never",
                    "developerInstructions": developer_instructions,
                }
            thread_result = await request(
                thread_method,
                thread_params,
                timeout=self._startup_timeout_seconds,
            )
            thread_id = thread_result["thread"]["id"]
            await emit(
                "runtime.thread",
                {
                    "thread_id": thread_id,
                    "action": (
                        "started"
                        if conversation_thread_id is None
                        else "resumed"
                    ),
                },
            )
            turn_result = await request(
                "turn/start",
                {
                    "threadId": thread_id,
                    "input": [{"type": "text", "text": prompt}],
                    "cwd": str(workspace_path),
                    "runtimeWorkspaceRoots": runtime_workspace_roots,
                    "approvalPolicy": "untrusted" if request_approval else "never",
                },
                timeout=self._startup_timeout_seconds,
            )
            turn_id = turn_result["turn"]["id"]

            while True:
                message = await read_message(self._turn_timeout_seconds)
                if "id" in message and "method" in message:
                    await handle_server_request(message)
                    continue
                params = message.get("params") or {}
                message_turn_id = params.get("turnId")
                nested_turn_id = (params.get("turn") or {}).get("id")
                if message_turn_id not in {None, turn_id}:
                    continue
                if nested_turn_id not in {None, turn_id}:
                    continue
                if await handle_notification(message):
                    break

            return RuntimeResult(
                summary=final_message or "Local Codex completed the task.",
                root_cause=None,
                changes=changes,
                validation=commands,
                approvals=approvals,
                warnings=warnings,
                next_actions=[],
                runtime_thread_id=thread_id,
            )
        finally:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except TimeoutError:
                    process.kill()
                    await process.wait()
