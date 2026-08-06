# Deployment

## 0.23.0 development deployment

Harness concurrency defaults to three child Codex app-server processes. `AGENT_GATEWAY_HARNESS_MAX_PARALLEL_AGENTS` can lower the host limit. `AGENT_GATEWAY_APPROVAL_TIMEOUT_SECONDS` controls the persistent approval window. Each investigator receives a task-scoped Git clone under the configured workspace root.

Requirements:

* Docker Desktop with Docker Compose.
* Available ports 8000, 5173 and local-only 5432.
* Codex local login through ChatGPT or a Codex API Key.
* CAG does not receive, read or store the Codex API Key.
* A high-entropy `AGENT_GATEWAY_OPERATIONS_ADMIN_TOKEN` stored in ignored
  local configuration or the service environment.

Start:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The Compose deployment contains:

* `gateway`: FastAPI application.
* `worker`: durable interactive, knowledge and operations queue consumers.
* `frontend`: React production build served by Nginx.
* `postgres`: PostgreSQL 16 with pgvector and a named volume.
* `redis`: Redis 7 with append-only persistence.
* `agent_gateway_workspaces`: named volume for task Git clones.

PostgreSQL and Redis are published at `127.0.0.1:5432` and
`127.0.0.1:6379` for the trusted Windows host Gateway. Neither service is
published to the LAN.

The unified management console is available locally at `http://127.0.0.1:5173`
and on the network at `http://<CAG-host-IP>:5173`. It includes the API test
console, API audit monitor, enterprise knowledge, capability governance and the
self-operations issue center.
The issue list and evidence remain readable for operations visibility.
The primary issue detail is a structured decision brief. Complete runtime
artifacts remain available as collapsed audit evidence. Event history loads in
bounded sequence pages when the timeline is expanded.
Approval, rejection, manual implementation, manual evaluation and reopen calls
require `X-CAG-Admin-Token` and `X-CAG-Admin-Identity`. The management page
keeps these values in browser session storage and clears them when the browser
session ends.
The issue detail places the administrator decision panel before the AI brief.
Occurrence count never removes authority. Approval-ready issues can enter the
governed improvement workflow, while pending, revision-required,
triage-failed and external-action issues can be closed with an explicit
no-modification decision.
The independent Code Knowledge route exposes governed structural facts without
placing code graph controls on the source maintenance page.
Browser API and SSE requests use the same 5173 origin. Nginx forwards `/api`
to `CAG_GATEWAY_UPSTREAM`, which defaults to
`host.docker.internal:8000`.
HTML entry responses disable browser caching so a deployment immediately loads
the new content-hashed JavaScript and CSS assets.

Knowledge ingestion writes file-level rejection audit rows to the database and
one gzip JSONL archive per run. Configure
`AGENT_GATEWAY_KNOWLEDGE_REJECTION_ARCHIVE_DIR`,
`AGENT_GATEWAY_KNOWLEDGE_REJECTION_DB_RETENTION_DAYS` and
`AGENT_GATEWAY_KNOWLEDGE_REJECTION_ARCHIVE_RETENTION_DAYS`. Defaults retain
queryable database detail for 90 days and compressed archives for 365 days.
The archive directory must use persistent host or volume storage in production.

Knowledge source entries and rejection records store file sizes as PostgreSQL
`BIGINT`. ZIP, DUMP, backup, binary and files above
`AGENT_GATEWAY_KNOWLEDGE_MAX_FILE_BYTES` are recorded as metadata-only assets.
Their content is not opened for extraction. The source entries API and
Knowledge management page expose the processing decision and reason.

The console creates a CAG Conversation and keeps one Conversation SSE
connection open across turns. Each turn performs governed knowledge retrieval
before Codex app-server execution. Resource URIs stay inside the same approved
knowledge and Task audit boundary.

## Database migration

The container runs:

```text
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For local development, configure `backend/.env.local` with a PostgreSQL URL,
then run:

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

Local Codex execution requires:

1. A supported local Codex CLI.
2. A completed Codex login flow using ChatGPT or an API Key.
3. `codex login status` reporting `Logged in using ChatGPT` or `Logged in using an API key`.
4. `codex app-server` support.
5. A private `CODEX_HOME` policy that prevents task workspaces from reading credential material.

The Codex process runs on the trusted host. Start the host Gateway with:

```powershell
.\scripts\run-local-codex-gateway.ps1
```

The script prefers the Codex plugin app-server executable installed under the current user profile, checks ChatGPT or API Key login status, PostgreSQL connectivity and the pgvector extension, then starts an API process and an independent durable queue worker process with `AGENT_GATEWAY_RUNTIME_PROVIDER=codex-app-server`. The Gateway binds to `0.0.0.0:8000` by default. Local callers use `http://127.0.0.1:8000`; network callers use `http://<CAG-host-IP>:8000`. The launcher terminates the peer process when either child exits so the supervisor can recover the complete pair. The script handles native login-status output consistently in Windows PowerShell 5 and PowerShell 7.

For a continuously supervised host deployment, register and start the Windows
background task:

```powershell
.\scripts\manage-local-codex-gateway-task.ps1 start
```

Use the same script with `status`, `stop` or `uninstall` to inspect, stop or
remove the background task. The task starts at Windows startup and at sign-in
under the current interactive user identity so the local Codex
authentication remains available. Task Scheduler retries the supervisor up to
999 times at one-minute intervals. The supervisor checks `/health/live` every
15 seconds, restarts a recognized Gateway after four consecutive liveness failures, and
starts it again when the listener exits. It never terminates an unexpected
port owner.

Supervisor logs are stored under
`workspaces\.gateway\logs\gateway-supervisor.log`. Each file is limited to
10 MiB and five rotated files are retained. Status and stop operations verify
the actual port listener because the Windows virtual-environment launcher can
leave the runtime Python child active after the scheduler action completes.
Starting the task replaces a prior loopback-only managed listener and verifies
that the resulting address is `0.0.0.0` or `::`.

When the Gateway is unavailable, the supervisor writes startup and readiness
failures to `workspaces\.gateway\logs\operational-issue-spool.jsonl`. After the
Gateway becomes ready, the supervisor submits each event to the issue intake
API. Stable external event IDs make replay idempotent, and unsuccessful
submissions remain in the spool.

The host Gateway requires PostgreSQL with pgvector. Configure the connection in
the ignored `backend/.env.local` file or the
`AGENT_GATEWAY_DATABASE_URL` environment variable. The managed runtime rejects
SQLite.

When sibling directory `D:\workspace\codex-selfimp` exists, the script configures it as the self-improvement root. An explicit `AGENT_GATEWAY_SELF_IMPROVEMENT_ROOT` value takes precedence.

The default Compose Gateway explicitly uses Fake Runtime. A future container deployment requires a dedicated authenticated host-side runtime bridge because ChatGPT credentials are not copied into containers.

## Local runtime settings

| Setting | Purpose |
|---|---|
| `AGENT_GATEWAY_DATABASE_URL` | PostgreSQL pgvector connection URL |
| `AGENT_GATEWAY_PROCESS_ROLE` | `api`, `worker` or isolated-test `combined` role |
| `AGENT_GATEWAY_RUNTIME_PROVIDER` | `fake` or `codex-app-server` |
| `AGENT_GATEWAY_CODEX_EXECUTABLE` | Callable local Codex executable |
| `AGENT_GATEWAY_CODEX_STARTUP_TIMEOUT_SECONDS` | Protocol initialization timeout |
| `AGENT_GATEWAY_CODEX_TURN_TIMEOUT_SECONDS` | Turn completion timeout |
| `AGENT_GATEWAY_CODEX_REQUIRE_CHATGPT_AUTH` | `true` enforces ChatGPT only; `false` allows ChatGPT or API Key local Codex sessions |
| `AGENT_GATEWAY_SELF_IMPROVEMENT_ROOT` | Parent directory for task-scoped self-improvement candidates |
| `AGENT_GATEWAY_QUEUE_HEARTBEAT_SECONDS` | Active job lease renewal and cancellation check interval, default 1 second |
| `AGENT_GATEWAY_QUEUE_OPERATIONS_WORKERS` | Independent self-operations issue Worker count |
| `AGENT_GATEWAY_KNOWLEDGE_SOURCES_DIR` | Managed Git and SVN source snapshot directory |
| `AGENT_GATEWAY_KNOWLEDGE_MAX_FILE_BYTES` | Maximum accepted source file size |
| `AGENT_GATEWAY_KNOWLEDGE_MAX_SPREADSHEET_CELLS` | Maximum populated cells extracted from one XLSX workbook, default 250000 |
| `AGENT_GATEWAY_KNOWLEDGE_CANDIDATE_LIMIT` | Maximum bounded candidates retained per retrieval channel |
| `AGENT_GATEWAY_KNOWLEDGE_FAST_TIMEOUT_SECONDS` | Overall indexed fast-search deadline |
| `AGENT_GATEWAY_KNOWLEDGE_BALANCED_TIMEOUT_SECONDS` | Overall balanced-search deadline |
| `AGENT_GATEWAY_KNOWLEDGE_DEEP_TIMEOUT_SECONDS` | Overall deep-search and extraction deadline |
| `AGENT_GATEWAY_KNOWLEDGE_STATEMENT_TIMEOUT_MS` | PostgreSQL timeout for each retrieval transaction |
| `AGENT_GATEWAY_KNOWLEDGE_SCHEDULER_ENABLED` | Enable persistent scheduled source synchronization |
| `AGENT_GATEWAY_KNOWLEDGE_SCHEDULER_POLL_SECONDS` | Poll interval for due sources |
| `AGENT_GATEWAY_KNOWLEDGE_SCHEDULER_LEASE_SECONDS` | Database lease duration for one claimed source |
| `AGENT_GATEWAY_SVN_EXECUTABLE` | SVN command line executable |
| `AGENT_GATEWAY_KNOWLEDGE_ENABLED` | Enable the enterprise knowledge plane |
| `AGENT_GATEWAY_OLLAMA_BASE_URL` | Private local Ollama endpoint |
| `AGENT_GATEWAY_OLLAMA_EMBEDDING_MODEL` | Embedding model name |
| `AGENT_GATEWAY_OLLAMA_MEMORY_MODEL` | Memory extraction and reranking model |
| `AGENT_GATEWAY_OLLAMA_EMBEDDING_DIMENSIONS` | Stored vector dimensions, fixed at 1024 |
| `AGENT_GATEWAY_KNOWLEDGE_ALLOWED_ROOTS` | Semicolon separated source root allowlist |

The self improvement root also contains `installation-receipts`. The Promotion
Service writes one JSON receipt for each Gateway activation and rollback.
Operators should back up this directory with the database audit records.

The startup path detects legacy local databases that were created before
Alembic version tracking. A complete recognized schema is stamped at its exact
historical revision and then upgraded. A partial or ambiguous core schema fails
closed and requires operator review.

Alembic revision `20260728_0010` keeps existing sources in `manual` mode.
Operators can enable scheduled synchronization per source through the Knowledge
page or source PATCH API. New web registrations default to scheduled mode.
The scheduler starts only when the knowledge plane and scheduler setting are
both enabled.

## SQLite to pgvector cutover

The legacy SQLite source remains active until its current learning run reaches a
terminal state. The migration command refuses active knowledge ingestions and
active Agent tasks.

The normal Windows launcher applies Alembic revision `20260806_0021` and then
runs the guarded automatic cutover. When the legacy source has no active work,
the launcher creates a consistent snapshot, replaces application tables inside
one PostgreSQL transaction, validates row counts, UUID digests, vectors and the
HNSW index, then writes `data_migration_receipts`. A matching receipt makes
later starts idempotent. The SQLite source is retained.

After the cutover and Redis readiness check, the launcher rebuilds and refreshes
the frontend container with `docker compose up -d --no-deps frontend`. This
updates port `5173` without starting or replacing the Compose Gateway service.

Create a fresh PostgreSQL database and set its target URL in the current
PowerShell session:

```powershell
docker exec cag-postgres-1 createdb `
  -U agent_gateway agent_gateway_pgvector
$env:AGENT_GATEWAY_MIGRATION_TARGET_URL = `
  "postgresql+psycopg://agent_gateway:<password>@127.0.0.1:5432/agent_gateway_pgvector"
```

Initialize the target schema, then run the migration in read-only preflight
mode:

```powershell
$env:AGENT_GATEWAY_DATABASE_URL = `
  $env:AGENT_GATEWAY_MIGRATION_TARGET_URL
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
cd ..
.\scripts\migrate-sqlite-to-pgvector.ps1
```

Review `migration_report.json` and `migration_report.md`. The receipt must show
SQLite integrity `ok`, zero active ingestions, matching table counts, matching
physical ID digests, matching vector counts, dimension 1024 and an HNSW index.

After the preflight passes, execute the same migration with explicit write
authorization:

```powershell
.\scripts\migrate-sqlite-to-pgvector.ps1 -Apply
```

To intentionally replace an already initialized target with the final legacy
snapshot, use the same transactional mode as automatic startup:

```powershell
.\scripts\migrate-sqlite-to-pgvector.ps1 -Apply -ReplaceTarget
```

Point `backend/.env.local` at the verified PostgreSQL database and start the
Gateway. `/health/ready` must report `backend` equal to `postgresql`,
`native_vector_search` equal to `true` and a pgvector version. Keep the legacy
SQLite source as an offline read-only rollback artifact. It is no longer a
runtime database after cutover.

Alembic revision `20260728_0011` adds code symbols, code relationships and
code-document links. Existing indexed sources require one subsequent ingestion
to populate structural facts. Unchanged document vectors remain reusable after
that run.

The Gateway image installs `tree-sitter-language-pack` and prefetches the
supported grammar set during image build. Production image construction
therefore requires package and grammar network access once. Running containers
use the cached grammars and do not download parsers while processing a source.
Windows host execution catches application-control blocks on native parser DLLs
and uses the audited language fallback.

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
