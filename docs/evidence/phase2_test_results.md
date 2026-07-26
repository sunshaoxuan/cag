# Phase 2 test results

Date: 2026-07-27

Version: 0.2.0

## Automated tests

Backend command:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing --cov-fail-under=90
```

Result:

```text
18 passed
Total coverage: 94.05 percent
```

Frontend commands:

```powershell
cd frontend
pnpm test
pnpm build
```

Result:

```text
3 passed
Vite production build passed
```

## Container integration

* `docker compose config --quiet` passed.
* Frontend and Gateway images built successfully.
* Frontend, Gateway, PostgreSQL and Redis reached healthy state.
* PostgreSQL applied migration `20260727_0002`.
* `GET /api/v1/projects` returned the configured `cag` project.
* Two tasks completed with distinct workspace IDs.
* Both cloned `origin/master` at commit `597b0edc4a5a167799201b750104e8ef010ad688`.
* The happy path returned ordered event sequences 1 through 8.

## Browser validation

The production frontend was opened at `http://127.0.0.1:5173`.

Validated behavior:

* Project configuration loaded.
* Prompt submission enabled only after text input.
* Task completed through eight visible events.
* Workspace state displayed as independent.
* Final validation report rendered.
* Browser console contained zero warnings and zero errors.

Screenshot: `docs/evidence/screenshots/phase2-task-completed.png`.

The final screenshot labels the target as `本地 Codex 订阅架构`.

## Runtime boundary

All Phase 2 runtime tests used `FakeAgentRuntime`. They did not call OpenAI Platform APIs and did not consume Codex subscription quota. Phase 3 owns the live local Codex subscription smoke test.
