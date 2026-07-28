# Phase 1 command record

Date: 2026-07-27

Commands containing credentials or credential contents are excluded. No credential value was read.

## Repository

```powershell
git fetch --prune origin
git ls-remote --heads origin
git branch -m master
git status --short --branch
```

## Specification

The DOCX was read through `python-docx` with bundled Python 3.12. It reported 184 paragraphs, no tables and one section.

## Codex runtime

```powershell
codex.exe --version
codex.exe login status
codex.exe app-server --help
codex.exe exec --help
```

The executable used was the local plugin app-server CLI recorded in ADR 0001.

## Dependency verification

Current versions were queried from the PyPI JSON registry for FastAPI, Pydantic, Pydantic Settings, SQLAlchemy, Alembic, Psycopg, Uvicorn, Pytest, Pytest Cov and HTTP client dependencies.

## Local validation

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app
git diff --check
```

## Container validation

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --no-color --tail 30 gateway
```

## Database validation

```powershell
docker compose exec -T postgres psql -U agent_gateway -d agent_gateway -tAc "select version_num from alembic_version"
docker compose exec -T postgres psql -U agent_gateway -d agent_gateway -tAc "select tablename from pg_tables where schemaname='public' order by tablename"
```

## HTTP smoke validation

```text
GET  /health/ready
POST /api/v1/tasks
GET  /api/v1/tasks/{task_id}
GET  /api/v1/tasks/{task_id}/events
```

## Phase 2 validation

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing --cov-fail-under=90

cd ..\frontend
pnpm test
pnpm build

cd ..
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose exec -T gateway alembic current
```

Live Phase 2 checks:

```text
GET  /api/v1/projects
GET  /api/v1/projects/{project_reference}
POST /api/v1/tasks
GET  /api/v1/tasks/{task_id}
GET  /api/v1/tasks/{task_id}/events?follow=false
GET  http://127.0.0.1:5173/health
```

The task console was tested in the in-app browser at `http://127.0.0.1:5173`. Prompt submission, eight ordered events, final report, browser console and a full-page screenshot were checked.

## Phase 3 local subscription validation

Local capability and account boundary:

```powershell
codex.exe --version
codex.exe login status
codex.exe app-server generate-json-schema --experimental --out <task-temp-dir>
```

Host Gateway:

```powershell
.\scripts\run-local-codex-gateway.ps1
```

Live validation called:

```text
GET  http://127.0.0.1:8001/health/ready
POST http://127.0.0.1:8001/api/v1/tasks
GET  http://127.0.0.1:8001/api/v1/tasks/{task_id}
GET  http://127.0.0.1:8001/api/v1/tasks/{task_id}/events?follow=false
```

The live Prompt requested one fixed response line under the read-only profile. The result was `GATEWAY_LOCAL_CODEX_SUBSCRIPTION_OK`.

## 0.4.0 persistent Conversation validation

```text
POST /api/v1/conversations
GET  /api/v1/conversations/{conversation_id}
POST /api/v1/tasks with conversation_id
GET  /api/v1/conversations/{conversation_id}/events?follow=false
POST /api/v1/tasks with the same conversation_id
GET  /api/v1/conversations/{conversation_id}/events?after_sequence=8&follow=false
```

The first Task returned `CAG-PERSIST-7F3A91`. The second Task used a different workspace, emitted `runtime.thread` action `resumed`, and returned the same marker.

## 0.4.0 deterministic validation

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
pnpm test
pnpm build

cd ..
docker compose config --quiet
docker compose build gateway frontend
```

## Truthful runtime feedback validation

Reload the managed host Gateway and rebuild only the frontend service:

```powershell
.\scripts\manage-local-codex-gateway-task.ps1 stop
.\scripts\manage-local-codex-gateway-task.ps1 start
docker compose build frontend
docker compose up -d --no-deps frontend
```

Replay the tail of a completed Conversation:

```text
GET /api/v1/conversations/{conversation_id}/events?follow=false
Last-Event-ID: 189
```

The real local Codex run persisted 197 events, including 188
`agent.message.delta` events. The browser verified live answer projection,
complete feedback, the 20-row display limit and zero console errors.

## 0.8.1 all-interface listener validation

```powershell
Invoke-Pester -Script scripts\tests\LocalCodexGateway.Tests.ps1

cd backend
.\.venv\Scripts\python.exe -m pytest

cd ..\frontend
pnpm test
pnpm build

cd ..
docker compose config --quiet
Get-NetTCPConnection -LocalPort 8000 -State Listen
Invoke-RestMethod http://127.0.0.1:8000/health/ready
Invoke-RestMethod http://<preferred-host-ipv4>:8000/health/ready
git diff --check
```

The managed task migrated the prior loopback listener to `0.0.0.0:8000`.
Both readiness probes returned `ready` and version `0.8.1`.

The staged index was archived into a task-local validation directory and tested
independently from concurrent working-tree changes. The first archive exposed
the incorrectly ignored Workspace Manager module. After anchoring the root
ignore rule and adding that module, the staged-tree checks were repeated.
