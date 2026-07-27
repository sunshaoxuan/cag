# Deployment

## 0.6.0 development deployment

Harness concurrency defaults to three child Codex app-server processes. `AGENT_GATEWAY_HARNESS_MAX_PARALLEL_AGENTS` can lower the host limit. `AGENT_GATEWAY_APPROVAL_TIMEOUT_SECONDS` controls the persistent approval window. Each investigator receives a task-scoped Git clone under the configured workspace root.

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
* `postgres`: PostgreSQL 16 with pgvector and a named volume.
* `redis`: Redis 7 with append-only persistence.
* `agent_gateway_workspaces`: named volume for task Git clones.

PostgreSQL and Redis are reachable only through the Compose network.

The task console is available at `http://127.0.0.1:5173`. It calls the Gateway at `http://127.0.0.1:8000`.

The console creates a CAG Conversation and keeps one Conversation SSE connection open across turns.

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

The script prefers the Codex plugin app-server executable installed under the current user profile, checks ChatGPT login status and starts the Gateway with `AGENT_GATEWAY_RUNTIME_PROVIDER=codex-app-server`. It handles native login-status output consistently in Windows PowerShell 5 and PowerShell 7.

For an interactive desktop test that must remain available after the launching shell exits, register and start the on-demand background task:

```powershell
.\scripts\manage-local-codex-gateway-task.ps1 start
```

Use the same script with `status`, `stop` or `uninstall` to inspect, stop or remove the background task. The task has no automatic trigger and runs only when explicitly started. Status and stop operations verify the actual port listener because the Windows virtual-environment launcher can leave the runtime Python child active after the scheduler action completes.

The host Gateway stores its SQLite runtime state under `workspaces/.gateway`, which is excluded from version control. An explicit `AGENT_GATEWAY_DATABASE_URL` value takes precedence.

When sibling directory `D:\workspace\codex-selfimp` exists, the script configures it as the self-improvement root. An explicit `AGENT_GATEWAY_SELF_IMPROVEMENT_ROOT` value takes precedence.

The default Compose Gateway explicitly uses Fake Runtime. A future container deployment requires a dedicated authenticated host-side runtime bridge because ChatGPT credentials are not copied into containers.

## Local runtime settings

| Setting | Purpose |
|---|---|
| `AGENT_GATEWAY_RUNTIME_PROVIDER` | `fake` or `codex-app-server` |
| `AGENT_GATEWAY_CODEX_EXECUTABLE` | Callable local Codex executable |
| `AGENT_GATEWAY_CODEX_STARTUP_TIMEOUT_SECONDS` | Protocol initialization timeout |
| `AGENT_GATEWAY_CODEX_TURN_TIMEOUT_SECONDS` | Turn completion timeout |
| `AGENT_GATEWAY_CODEX_REQUIRE_CHATGPT_AUTH` | Reject non-ChatGPT account types |
| `AGENT_GATEWAY_SELF_IMPROVEMENT_ROOT` | Parent directory for task-scoped self-improvement candidates |

The self improvement root also contains `installation-receipts`. The Promotion
Service writes one JSON receipt for each Gateway activation and rollback.
Operators should back up this directory with the database audit records.

The startup path detects legacy local databases that were created before
Alembic version tracking. A complete recognized schema is stamped at its exact
historical revision and then upgraded. A partial or ambiguous core schema fails
closed and requires operator review.
| `AGENT_GATEWAY_KNOWLEDGE_ENABLED` | Enable the enterprise knowledge plane |
| `AGENT_GATEWAY_OLLAMA_BASE_URL` | Private local Ollama endpoint |
| `AGENT_GATEWAY_OLLAMA_EMBEDDING_MODEL` | Embedding model name |
| `AGENT_GATEWAY_OLLAMA_MEMORY_MODEL` | Memory extraction and reranking model |
| `AGENT_GATEWAY_OLLAMA_EMBEDDING_DIMENSIONS` | Stored vector dimensions, fixed at 1024 |
| `AGENT_GATEWAY_KNOWLEDGE_ALLOWED_ROOTS` | Semicolon separated source root allowlist |

## Managed local Ollama

The existing Docker volume named `ollama` remains the model system of record.
Run the preflight first:

```powershell
.\scripts\setup-local-knowledge.ps1
```

Apply the verified migration:

```powershell
.\scripts\setup-local-knowledge.ps1 -Apply
```

The managed container uses a pinned image, one loaded model, one parallel model request and `127.0.0.1:11434`. The script records the prior container inspection under `.codex-tmp` and supports `-Rollback`.

Initialize the application encryption key under the current Windows identity:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.knowledge.keyring_cli init
```

Both local drives are currently unencrypted. The readiness and standards evidence retain this production admission warning because vector and keyword indices require encrypted host storage for complete static protection.

## Production gate

Production deployment is blocked until authentication, project authorization, rate limiting, concurrency controls, runtime sandbox enforcement, workspace cleanup, command policy, approvals, Secret Scanner and audit controls pass their acceptance tests.
