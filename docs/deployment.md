# Deployment

## Phase 3 development deployment

Requirements:

* Docker Desktop with Docker Compose.
* Available ports 8000 and 5173.
* No OpenAI Platform API Key.

Start:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The Compose deployment contains:

* `gateway`: FastAPI application.
* `frontend`: React production build served by Nginx.
* `postgres`: PostgreSQL 16 with a named volume.
* `redis`: Redis 7 with append-only persistence.
* `agent_gateway_workspaces`: named volume for task Git clones.

PostgreSQL and Redis are reachable only through the Compose network.

The task console is available at `http://127.0.0.1:5173`. It calls the Gateway at `http://127.0.0.1:8000`.

## Database migration

The container runs:

```text
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For local development:

```powershell
cd backend
.\.venv\Scripts\alembic.exe upgrade head
```

## Health verification

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
Invoke-WebRequest http://127.0.0.1:5173/health
```

## Project and workspace configuration

Project definitions are mounted read-only from `projects` into the Gateway image. `AGENT_GATEWAY_PROJECTS_DIR` selects that directory and `AGENT_GATEWAY_WORKSPACE_ROOT` selects the workspace root.

Each task clones the configured default branch into:

```text
workspaces/{project_physical_id}/{task_id}
```

The cloned commit SHA is persisted with the Task. Named volumes are retained by `docker compose down` and removed only when the operator explicitly requests volume deletion.

## Local Codex runtime prerequisites

Local subscription execution requires:

1. A supported local Codex CLI.
2. A completed `codex login` ChatGPT browser flow.
3. `codex login status` reporting `Logged in using ChatGPT`.
4. `codex app-server` support.
5. A private `CODEX_HOME` policy that prevents task workspaces from reading credential material.

The Codex process runs on the trusted host. Start the host Gateway with:

```powershell
.\scripts\run-local-codex-gateway.ps1
```

The script prefers the Codex plugin app-server executable installed under the current user profile, checks ChatGPT login status and starts the Gateway with `AGENT_GATEWAY_RUNTIME_PROVIDER=codex-app-server`.

The default Compose Gateway explicitly uses Fake Runtime. A future container deployment requires a dedicated authenticated host-side runtime bridge because ChatGPT credentials are not copied into containers.

## Local runtime settings

| Setting | Purpose |
|---|---|
| `AGENT_GATEWAY_RUNTIME_PROVIDER` | `fake` or `codex-app-server` |
| `AGENT_GATEWAY_CODEX_EXECUTABLE` | Callable local Codex executable |
| `AGENT_GATEWAY_CODEX_STARTUP_TIMEOUT_SECONDS` | Protocol initialization timeout |
| `AGENT_GATEWAY_CODEX_TURN_TIMEOUT_SECONDS` | Turn completion timeout |
| `AGENT_GATEWAY_CODEX_REQUIRE_CHATGPT_AUTH` | Reject non-ChatGPT account types |

## Production gate

Production deployment is blocked until authentication, project authorization, rate limiting, concurrency controls, runtime sandbox enforcement, workspace cleanup, command policy, approvals, Secret Scanner and audit controls pass their acceptance tests.
