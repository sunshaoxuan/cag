# Phase 4 test results

Date: 2026-07-27

Version: 0.4.0

## Automated tests

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```text
36 passed
Total coverage: 91.06 percent
```

Frontend:

```powershell
cd frontend
pnpm test
pnpm build
```

Result:

```text
3 passed
Production build passed
```

Covered behavior:

* Conversation creation and query.
* Task history by Conversation.
* Persistent Codex thread mapping.
* `thread/start` and `thread/resume`.
* Ephemeral one-turn Tasks.
* Conversation event sequencing.
* SSE resume through `Last-Event-ID`.
* Project Runtime Profile allowlist.
* Task-specific self-improvement candidate root.
* Continuous conversation frontend.
* One persistent EventSource reused by multiple turns.

## Real local ChatGPT subscription smoke

* Gateway version: 0.4.0.
* Authentication: local ChatGPT login.
* First result: `CAG-PERSIST-7F3A91`.
* Second result: `CAG-PERSIST-7F3A91`.
* Thread action sequence: `started`, `resumed`.
* Conversation SSE IDs: 1 through 16.
* Distinct Task workspace IDs: confirmed.
* API Key: absent from the runtime contract.

## Real self-improvement candidate smoke

Runtime Profile:

```text
self-improvement-candidate
```

Task:

```text
921327c4-f867-40dc-99d0-3d55c63212cd
```

Created only inside the assigned candidate root:

```text
D:\workspace\codex-selfimp\outputs\cag-921327c4-f867-40dc-99d0-3d55c63212cd\CANDIDATE.md
D:\workspace\codex-selfimp\outputs\cag-921327c4-f867-40dc-99d0-3d55c63212cd\TASK_LEARNING_RECEIPT.md
```

The isolated project workspace remained clean. The receipt records `install_status: proposed`.

An earlier broad investigation Task was manually terminated after it spent several minutes exploring missing dependencies in the last pushed 0.3.0 clone. This establishes the need for task cancellation and investigation budgets in a later control-plane phase. The scoped retry completed successfully.

## Remaining closure

## Compose and browser validation

* Gateway, frontend, PostgreSQL and Redis: healthy.
* Applied Alembic revision: `20260727_0004`.
* Gateway health version: `0.4.0`.
* Two browser turns used one visible CAG Conversation ID.
* Conversation event sequence continued from 1 through 16.
* Both Fake Runtime final messages rendered in the chat history.
* Browser console warnings and errors: 0.
* Screenshot: `docs/evidence/screenshots/phase4-continuous-conversation.png`.
