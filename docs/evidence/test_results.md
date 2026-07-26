# Phase 1 test results

Date: 2026-07-27

Version: 0.1.0

## Automated tests

Command:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```text
14 passed
Total coverage: 96.75 percent
Warnings: 0
```

Covered behavior:

* Liveness and readiness.
* Task creation and query.
* Stable Project physical ID resolution.
* Missing physical Project handling.
* Conversation reference validation.
* Prompt validation.
* Ordered SSE events.
* SSE resume after sequence.
* Missing task handling.
* Runtime failure persistence.
* Fake Runtime deterministic output.
* Alembic Phase 1 schema upgrade.
* Release version consistency.

## Static checks

| Check | Result |
|---|---|
| Python bytecode compile | Passed |
| `git diff --check` | Passed |
| Compose config parse | Passed |

## Container integration

| Service | Result |
|---|---|
| Gateway | Healthy |
| PostgreSQL | Healthy |
| Redis | Healthy |

Applied migration:

```text
20260727_0001
```

Tables:

```text
alembic_version
conversations
projects
task_events
tasks
```

## Live HTTP smoke

Task creation returned HTTP 202 with status `queued`. The task progressed through `running` to `completed`. SSE returned six ordered events:

```text
task.created
task.started
agent.plan
agent.message
test.completed
task.completed
```

The final report contains a passed Fake Runtime validation. No OpenAI API or Codex subscription call occurred.
