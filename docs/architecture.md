# Agent Gateway Architecture

## 1. Purpose

Agent Gateway receives a project reference and natural language Prompt, resolves policy and runtime configuration, runs a local Codex agent in an isolated workspace, streams structured events, pauses for approvals, and stores auditable results.

Phase 3 adds a real local Codex app-server adapter authenticated through the existing ChatGPT subscription session. Configuration-driven projects, isolated task clones and the browser console remain the execution foundation.

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

Validation integration:

* `FakeAgentRuntime` emits deterministic events and final output.
* Tests never call Codex and never consume subscription credits.

Phase 3 production-path integration:

* One local `codex app-server --stdio` child process is started per Gateway task.
* The Gateway performs protocol initialization and then calls `account/read`.
* The task is rejected unless the reported account type is `chatgpt`.
* A Codex thread and turn run inside the task workspace.
* App-server notifications map into durable Gateway events and a structured final report.
* The Gateway never reads the Codex credential store.

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

## 4. Phase 3 components

### API

FastAPI exposes health, Project and Task APIs. A React console submits tasks and renders named SSE events.

### Task service

The service loads `projects/*.yaml`, synchronizes configured Project metadata, creates Task and TaskEvent records, and resolves either a business Code or physical UUID into the stored Project physical ID.

### Task executor

The executor changes a task from `queued` to `preparing`, creates its isolated Git workspace, records the resolved commit, moves to `running`, invokes the selected runtime, stores every emitted event in sequence, and closes the task as `completed` or `failed`.

### Fake runtime

The runtime emits a plan, an agent message, validation output and a structured final report. Output is deterministic for repeatable tests.

### Event stream

The SSE endpoint reads committed TaskEvent rows in sequence order. `after_sequence` supports reconnection and `follow` controls live polling.

### Persistence

SQLAlchemy 2 models are used with PostgreSQL in containers and SQLite in tests. Alembic owns schema versioning through revision `20260727_0002`. Local development can create missing tables; container deployment runs Alembic before serving traffic.

### Project registry

Each YAML file declares a stable physical ID, business Code, repository, default branch, workspace mode, instruction files and permitted runtime profiles. Repository metadata is synchronized into PostgreSQL while strong references continue to use the physical ID.

### Workspace manager

The manager creates `workspaces/{project_physical_id}/{task_id}`, clones only the configured default branch, resolves `HEAD`, and returns a public workspace identifier without returning the host filesystem path through the API.

### Frontend

The React console loads configured projects, submits a Prompt, subscribes to named SSE events, keeps them ordered by sequence, and retrieves the final task report on a terminal event.

### Local Codex app-server runtime

The adapter communicates through stdio JSONL. It declares the experimental API capability required by `runtimeWorkspaceRoots`, verifies ChatGPT authentication, creates an ephemeral thread and starts one turn.

`read-only-analysis` selects the read-only sandbox. Other Phase 3 profiles select workspace-write. Approval policy remains `never` until durable pause and resume support is released in Phase 5. Any approval callback is declined and recorded.

## 5. Data identity

Every business record has an independent UUID physical ID.

* `Project.code` is a unique business identifier.
* `Conversation.project_id` references `Project.id`.
* `Task.project_id` references `Project.id`.
* `Task.conversation_id` references `Conversation.id`.
* `TaskEvent.task_id` references `Task.id`.

The request field `project_id` accepts a project UUID or project Code for compatibility with the source specification. Storage always uses the physical UUID. Responses expose `project_id` and `project_code`.

## 6. Task lifecycle

```text
POST /tasks
  |
validate request
  |
resolve configured project
  |
create queued task and task.created event
  |
background executor
  |
task.started
  |
workspace.preparing
  |
clone configured branch into task workspace
  |
workspace.ready
  |
runtime events
  |
task.completed or task.failed
```

Terminal states are `completed`, `failed`, and `cancelled`.

## 7. Runtime isolation

Phase 2 allocates one writable Git clone per task:

```text
workspaces/{project_id}/{task_id}
```

The runtime receives its task workspace path. Concurrent tasks have distinct physical directories. Phase 4 will enforce the complete filesystem permission boundary for explicitly allowed read paths.

## 8. Security boundaries

* Gateway authentication governs which users can access projects.
* Runtime profiles narrow filesystem, shell, network, database and Git capabilities.
* Policy Engine classifies commands independently of the Prompt.
* App-server credentials stay in the local Codex credential store.
* The Gateway never reads, copies, returns, or logs Codex credential material.
* External listeners require Gateway authentication. Codex app-server remains a private local child process or loopback service.

## 9. Observability

Phase 2 records task ID, project ID, workspace ID, workspace commit, event type, sequence and timestamp. Later phases add user ID, model, Prompt version, Skill version, token usage, duration, approvals, Git diff and test artifacts. OpenTelemetry integration belongs to the observability phase.

## 10. Defaults

Noncritical defaults are controlled by settings and recorded in ADR 0002:

* Development database: local SQLite file.
* Container database: PostgreSQL 16.
* Redis: Redis 7.
* Container runtime: Fake Runtime for deterministic tests.
* Host runtime: `codex-app-server` when started through `scripts/run-local-codex-gateway.ps1`.
* Fake event delay: 25 milliseconds.
* SSE poll interval: 100 milliseconds.
* Runtime profile: `general-engineering`.
* Project configuration directory: `projects`.
* Workspace root: `workspaces`.
* Workspace type: `git_clone`.
