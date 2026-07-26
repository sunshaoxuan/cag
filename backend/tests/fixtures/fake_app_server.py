import json
import sys


account_type = sys.argv[1] if len(sys.argv) > 1 else "chatgpt"
mode = sys.argv[2] if len(sys.argv) > 2 else "normal"


def send(message: dict[str, object]) -> None:
    print(json.dumps(message), flush=True)


for raw_line in sys.stdin:
    message = json.loads(raw_line)
    method = message.get("method")
    request_id = message.get("id")
    if method == "initialize":
        if mode == "invalid-json":
            print("not-json", flush=True)
            break
        send({"id": request_id, "result": {"userAgent": "fake-app-server"}})
    elif method == "initialized":
        continue
    elif method == "account/read":
        account = {"type": account_type}
        if account_type == "chatgpt":
            account.update({"email": None, "planType": "pro"})
        send(
            {
                "id": request_id,
                "result": {
                    "account": account,
                    "requiresOpenaiAuth": True,
                },
            }
        )
    elif method == "thread/start":
        send(
            {
                "id": request_id,
                "result": {"thread": {"id": "thread-1"}},
            }
        )
    elif method == "turn/start":
        send(
            {
                "id": request_id,
                "result": {
                    "turn": {"id": "turn-1", "items": [], "status": "inProgress"}
                },
            }
        )
        if mode == "approval":
            send(
                {
                    "id": 900,
                    "method": "item/commandExecution/requestApproval",
                    "params": {"threadId": "thread-1", "turnId": "turn-1"},
                }
            )
            approval_response = json.loads(sys.stdin.readline())
            if approval_response.get("result", {}).get("decision") != "decline":
                raise RuntimeError("approval was not declined")
        if mode == "requests":
            for server_request, expected_key in [
                ("item/tool/requestUserInput", "answers"),
                ("item/permissions/requestApproval", "permissions"),
                ("unsupported/request", "error"),
            ]:
                send(
                    {
                        "id": 901,
                        "method": server_request,
                        "params": {
                            "threadId": "thread-1",
                            "turnId": "turn-1",
                        },
                    }
                )
                response = json.loads(sys.stdin.readline())
                if expected_key not in response.get("result", response):
                    raise RuntimeError(
                        f"missing {expected_key} for {server_request}"
                    )
        send(
            {
                "method": "turn/plan/updated",
                "params": {
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "plan": [{"step": "inspect", "status": "completed"}],
                    "explanation": "fixture",
                },
            }
        )
        command = {
            "id": "item-command",
            "type": "commandExecution",
            "command": "git status --short",
            "commandActions": [],
            "cwd": ".",
            "status": "inProgress",
        }
        send(
            {
                "method": "item/started",
                "params": {
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "startedAtMs": 1,
                    "item": command,
                },
            }
        )
        command.update({"status": "completed", "exitCode": 0})
        send(
            {
                "method": "item/completed",
                "params": {
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "completedAtMs": 2,
                    "item": command,
                },
            }
        )
        send(
            {
                "method": "item/completed",
                "params": {
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "completedAtMs": 3,
                    "item": {
                        "id": "item-change",
                        "type": "fileChange",
                        "status": "completed",
                        "changes": [{"path": "README.md", "kind": "update"}],
                    },
                },
            }
        )
        send(
            {
                "method": "warning",
                "params": {"message": "fixture warning"},
            }
        )
        send(
            {
                "method": "error",
                "params": {"error": {"message": "recoverable fixture error"}},
            }
        )
        send(
            {
                "method": "item/completed",
                "params": {
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "completedAtMs": 4,
                    "item": {
                        "id": "item-message",
                        "type": "agentMessage",
                        "text": "LOCAL_CODEX_FIXTURE_OK",
                    },
                },
            }
        )
        send(
            {
                "method": "turn/completed",
                "params": {
                    "threadId": "thread-1",
                    "turn": {
                        "id": "turn-1",
                        "items": [],
                        "status": "completed",
                    },
                },
            }
        )
