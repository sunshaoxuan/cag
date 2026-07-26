# Agent Gateway Architecture

## 1. Purpose

Agent Gateway receives a project reference and natural language Prompt, resolves policy and runtime configuration, runs a local Codex agent in an isolated workspace, streams structured events, pauses for approvals, and stores auditable results.

Phase 1 establishes the service boundary and validates task lifecycle behavior with a deterministic Fake Runtime.

## 2. Runtime decision

The production direction is a local Codex runtime authenticated through the user's existing ChatGPT subscription session.

Primary integration:

* `codex app-server` over stdio JSONL.
* One initialized app-server client manages Codex threads and turns.
* App-server notifications map to Gateway task events.
* Approval requests remain suspended until the Gateway approval API resolves them.

Compatibility integration:

* `codex exec --json` executes a single task and emits JSONL events.
* It reuses saved Codex CLI authentication.
* It is suitable for controlled jobs where deep approval and conversation control are not required.

Phase 1 integration:

* `FakeAgentRuntime` emits deterministic events and final output.
* Tests never call Codex and never consume subscription credits.

The detailed decision and verified local capability are recorded in [ADR 0001](adr/0001-local-codex-runtime.md).

## 3. Logical architecture

```text
Web UI
  |
Gateway API
  |
Authentication and Authorization
  |
Task Router
  |
Runtime Profile Resolver
  |
Agent Runtime
  |-- Fake Runtime
  |-- Local Codex App Server
  |-- Codex Exec JSON Runner
  |-- MCP Client
  |
Isolated Workspace
  |-- Git Repository
  |-- AGENTS.md
  |-- Project Skills
  |-- Shared Skills
  |-- Shell and File Tools
  |
Approval Service
  |
Task Store, Audit Log and Artifacts
```

## 4. Phase 1 components

### API

FastAPI exposes health endpoints and the first Task API.

### Task service

The service creates Project, Task and TaskEvent records in one transaction. It resolves the Phase 1 compatible project reference into a Project physical ID.

### Task executor

The executor changes a task from `queued` to `running`, invokes the selected runtime, stores every emitted event in sequence, and closes the task as `completed` or `failed`.

### Fake runtime

The runtime emits a plan, an agent message, validation output and a structured final report. Output is deterministic for repeatable tests.

### Event stream

The SSE endpoint reads committed TaskEvent rows in sequence order. `after_sequence` supports reconnection and `follow` controls live polling.

### Persistence

SQLAlchemy 2 models are used with PostgreSQL in containers and SQLite in tests. Alembic owns schema versioning. Phase 1 application startup can create missing tables for local development; production deployment runs Alembic before serving traffic.

## 5. Data identity

Every business record has an independent UUID physical ID.

* `Project.code` is a unique business identifier.
* `Conversation.project_id` references `Project.id`.
* `Task.project_id` references `Project.id`.
* `Task.conversation_id` references `Conversation.id`.
* `TaskEvent.task_id` references `Task.id`.

The Phase 1 request field `project_id` accepts a project UUID or project Code for compatibility with the source specification. Storage always uses the physical UUID. Responses expose `project_id` and `project_code`.

## 6. Task lifecycle

```text
POST /tasks
  |
validate request
  |
resolve or create development project
  |
create queued task and task.created event
  |
background executor
  |
task.started
  |
runtime events
  |
task.completed or task.failed
```

Terminal states are `completed`, `failed`, and `cancelled`.

## 7. Runtime isolation roadmap

Phase 2 will allocate one writable task workspace per writing task:

```text
workspaces/{project_id}/{task_id}
```

The runtime receives only the task workspace plus explicitly allowed read paths. Concurrent writing tasks never share a Git worktree.

## 8. Security boundaries

* Gateway authentication governs which users can access projects.
* Runtime profiles narrow filesystem, shell, network, database and Git capabilities.
* Policy Engine classifies commands independently of the Prompt.
* App-server credentials stay in the local Codex credential store.
* The Gateway never reads, copies, returns, or logs Codex credential material.
* External listeners require Gateway authentication. Codex app-server remains a private local child process or loopback service.

## 9. Observability

Phase 1 records task ID, project ID, event type, sequence and timestamp. Later phases add conversation ID, user ID, model, Prompt version, Skill version, tool calls, token usage, duration, approvals, Git diff and test artifacts. OpenTelemetry integration belongs to the observability phase.

## 10. Defaults

Noncritical defaults are controlled by settings and recorded in ADR 0002:

* Development database: local SQLite file.
* Container database: PostgreSQL 16.
* Redis: Redis 7.
* Runtime: Fake Runtime until the local Codex adapter is enabled.
* Fake event delay: 25 milliseconds.
* SSE poll interval: 100 milliseconds.
* Runtime profile: `general-engineering`.
