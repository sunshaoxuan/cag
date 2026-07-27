# Agent Gateway Architecture

## 1. Purpose

Agent Gateway receives a project reference and natural language Prompt, resolves policy and runtime configuration, runs a local Codex agent in an isolated workspace, streams structured events, pauses for approvals, and stores auditable results.

Version 0.6.0 adds the governed parallel Agent Harness around the enterprise knowledge plane. Local Ollama performs embedding, retrieval support and memory extraction. ChatGPT-authenticated Codex remains the engineering Agent runtime. CAG owns child scheduling, single-writer enforcement, Artifact persistence, approval and unified SSE.

## 2. Runtime decision

The production direction is a local Codex runtime authenticated through the user's existing ChatGPT subscription session.

Primary integration:

* `codex app-server` over stdio JSONL.
* Each Task starts an initialized app-server client and selects the required Codex thread and turn.
* App-server notifications map to Gateway task events.
* Approval requests remain suspended until the Gateway approval API resolves them.

Compatibility integration:

* `codex exec --json` executes a single task and emits JSONL events.
* It reuses saved Codex CLI authentication.
* It is suitable for controlled jobs where deep approval and conversation control are not required.

Validation integration:

* `FakeAgentRuntime` emits deterministic events and final output.
* Tests never call Codex and never consume subscription credits.

Current production-path integration:

* One local `codex app-server --stdio` child process is started per Gateway task.
* The Gateway performs protocol initialization and then calls `account/read`.
* The task is rejected unless the reported account type is `chatgpt`.
* A one-turn Task without a Conversation uses an ephemeral Codex thread.
* The first Task in a Conversation starts a persisted Codex thread.
* Later Tasks resume the persisted Codex thread in their new isolated workspaces.
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

## 4. Current components

### API

FastAPI exposes health, Project, Conversation and Task APIs. The React console creates one Conversation, holds one CAG SSE connection and submits each user message as a Task.

### Task service

The service loads `projects/*.yaml`, synchronizes configured Project metadata, creates Task and TaskEvent records, and resolves either a business Code or physical UUID into the stored Project physical ID.

### Task executor

The executor changes a task from `queued` to `preparing`, creates its isolated Git workspace, records the resolved commit, moves to `running`, invokes the selected runtime, stores every emitted event in sequence, and closes the task as `completed` or `failed`.

### Fake runtime

The runtime emits a plan, an agent message, validation output and a structured final report. Output is deterministic for repeatable tests.

### Event streams

The Task SSE endpoint reads committed TaskEvent rows in Task sequence order and ends at a terminal Task state.

The Conversation SSE endpoint remains open across multiple Tasks. `Conversation.next_event_sequence` assigns a continuous sequence, heartbeat comments keep idle connections alive, and `Last-Event-ID` supports standard EventSource reconnection. The frontend never connects to Codex app-server.

The local runtime maps every permitted user-visible app-server delta into a durable event before SSE delivery. This includes Agent message, plan, command output and reasoning-summary deltas. Completed events remain authoritative snapshots. Hidden reasoning text and credential material are outside the feedback contract.

### Persistence

SQLAlchemy 2 models are used with PostgreSQL in containers and SQLite in tests. Alembic owns schema versioning through revision `20260727_0004`. Local development can create missing tables; container deployment runs Alembic before serving traffic.

### Project registry

Each YAML file declares a stable physical ID, business Code, repository, default branch, workspace mode, instruction files and permitted runtime profiles. Repository metadata is synchronized into PostgreSQL while strong references continue to use the physical ID.

### Workspace manager

The manager creates `workspaces/{project_physical_id}/{task_id}`, clones only the configured default branch, resolves `HEAD`, and returns a public workspace identifier without returning the host filesystem path through the API.

### Frontend

The React console loads configured projects, submits a Prompt, subscribes to named SSE events, keeps them ordered by sequence, projects live Agent message deltas into the active conversation bubble and retrieves the final task report on a terminal event.

Feedback controls are frontend projections over the complete CAG event sequence. Key, standard and full detail levels determine visible categories, while a row limit controls how many matching events are rendered. The controls never ask the backend to drop or rewrite events.

### Local Codex app-server runtime

The adapter communicates through stdio JSONL. It declares the experimental API capability required by `runtimeWorkspaceRoots`, verifies ChatGPT authentication and selects `thread/start` or `thread/resume` from the CAG Conversation mapping.

`read-only-analysis` selects the read-only sandbox. Executor selects workspace-write. Version 0.6.0 uses app-server approval policy `untrusted` when the persistent approval callback is configured. Command Policy Engine allows mechanical verification commands, denies destructive patterns and pauses other commands for a stored decision.

### Self-improvement candidate profile

`self-improvement-candidate` creates one directory under the configured self-improvement output root for the current Task. Only that directory is added to the app-server runtime workspace roots. Developer instructions require candidate files and a learning receipt and prohibit formal installation. See [self-improvement.md](self-improvement.md).

### Enterprise knowledge plane

Knowledge Sources bind to a Project and either its Tenant or ProductVersion. Ingestion reads approved local text files, scans and redacts secrets, creates encrypted chunks, requests 1024 dimensional embeddings from Ollama and stores them in PostgreSQL with pgvector.

Task retrieval uses tenant and product version filters before reciprocal rank fusion. CAG injects only approved, non-instructional evidence blocks into Codex developer instructions and records citation IDs without logging their plaintext. Completed Tasks can create encrypted MemoryCandidates through the local memory model.

Indexing and task feedback remain CAG-owned SSE streams. Frontends never connect to Ollama or Codex app-server directly.

## 5. Data identity

Every business record has an independent UUID physical ID.

* `Project.code` is a unique business identifier.
* `Conversation.project_id` references `Project.id`.
* `Conversation.codex_thread_id` stores one opaque runtime thread identity.
* `Task.project_id` references `Project.id`.
* `Task.conversation_id` references `Conversation.id`.
* `TaskEvent.task_id` references `Task.id`.
* Conversation TaskEvents also store `conversation_id` and a Conversation-local sequence.

The request field `project_id` accepts a project UUID or project Code for compatibility with the source specification. Storage always uses the physical UUID. Responses expose `project_id` and `project_code`.

## 6. Task lifecycle

```text
POST /conversations
  |
open CAG Conversation SSE
  |
POST /tasks with conversation_id
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
  |
keep Conversation SSE open for the next Task
```

Terminal states are `completed`, `failed`, and `cancelled`.

## 7. Runtime isolation

The Gateway allocates one writable Git clone per task:

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
