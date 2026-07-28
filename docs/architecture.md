# Agent Gateway Architecture

## 1. Purpose

Agent Gateway receives a project reference and natural language Prompt through
an external HTTP API, resolves policy and runtime configuration, runs a local
Codex agent in an isolated workspace, streams structured events, pauses for
approvals, and stores auditable results. The web application is an API test,
monitoring and governance client.

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
External business clients -----\
                                > Gateway Task API
Web API test console ----------/
                                  |
Authentication and Authorization
  |
Trace and idempotency boundary
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
  |
Global audit SSE
  |
External listeners and web monitor
```

## 4. Current components

### API

FastAPI exposes health, Project, Conversation, Task and Audit APIs. External
clients submit Task requests directly. The React test console creates one
Conversation, holds one CAG SSE connection and submits each user message through
the same public Task endpoint with source `test_console`.

### Task service

The service loads `projects/*.yaml`, synchronizes configured Project metadata,
creates Task and TaskEvent records, and resolves either a business Code or
physical UUID into the stored Project physical ID. Task admission stores the
client, caller request ID, source, request hash and optional idempotency key.

### Task executor

The executor changes a task from `queued` to `preparing`, creates its isolated Git workspace, records the resolved commit, moves to `running`, invokes the selected runtime, stores every emitted event in sequence, and closes the task as `completed` or `failed`.

### Fake runtime

The runtime emits a plan, an agent message, validation output and a structured final report. Output is deterministic for repeatable tests.

### Event streams

The Task SSE endpoint reads committed TaskEvent rows in Task sequence order and ends at a terminal Task state.

The Conversation SSE endpoint remains open across multiple Tasks. `Conversation.next_event_sequence` assigns a continuous sequence, heartbeat comments keep idle connections alive, and `Last-Event-ID` supports standard EventSource reconnection. The frontend never connects to Codex app-server.

Every TaskEvent receives a Gateway-wide sequence from the locked
`AuditCursor`. `/api/v1/audit/events` projects these committed events as one
resumable `audit.event` SSE. Source, client and task filters operate on the same
durable ledger. Runtime, Harness, knowledge, tool, command, approval, validation
and learning paths all call `TaskService.append_event`, so the global audit
stream observes the complete fact-event boundary automatically.

The local runtime maps every permitted user-visible app-server delta into a durable event before SSE delivery. This includes Agent message, plan, command output and reasoning-summary deltas. Completed events remain authoritative snapshots. Hidden reasoning text and credential material are outside the feedback contract.

### Persistence

SQLAlchemy 2 models are used with PostgreSQL in containers and SQLite in tests.
Alembic owns schema versioning through revision `20260727_0008`. Local
development can create missing tables; container deployment runs Alembic before
serving traffic.

### Project registry

Each YAML file declares a stable physical ID, business Code, repository, default branch, workspace mode, instruction files and permitted runtime profiles. Repository metadata is synchronized into PostgreSQL while strong references continue to use the physical ID.

### Workspace manager

The manager creates `workspaces/{project_physical_id}/{task_id}`, clones only the configured default branch, resolves `HEAD`, and returns a public workspace identifier without returning the host filesystem path through the API.

### Frontend

The React application on port 5173 is the unified visual management console.
Its overview, API audit, enterprise knowledge and capability routes provide
management functions, while the Conversation route provides the API test
console. Production browser traffic uses same-origin `/api` and SSE URLs.
Frontend Nginx proxies those requests to the host Gateway.

The React test console loads configured projects, submits a Prompt through the
public Task API, subscribes to named SSE events, keeps them ordered by sequence,
projects live Agent message deltas into the active conversation bubble and
retrieves the final task report on a terminal event. The audit page subscribes
to the Gateway-wide audit SSE and displays calls from both external clients and
the web test console.

Feedback controls are frontend projections over the complete CAG event sequence. Key, standard and full detail levels determine visible categories, while a row limit controls how many matching events are rendered. The controls never ask the backend to drop or rewrite events.

### Local Codex app-server runtime

The adapter communicates through stdio JSONL. It declares the experimental API capability required by `runtimeWorkspaceRoots`, verifies ChatGPT authentication and selects `thread/start` or `thread/resume` from the CAG Conversation mapping.

### Structural code knowledge

The knowledge plane has a semantic index and a structural code index. Text
chunks keep encrypted evidence and 1024 dimensional vectors. `CodeSymbol`
records addressable definitions with source locations. `CodeRelation` records
imports and calls and references a target symbol when resolution is
deterministic. `CodeDocumentLink` records direct path and symbol mentions in
non-code documents.

Ingestion scans and cleans the source once. Code analysis then creates
symbol-boundary chunks and parser facts before embedding. Changed documents
replace their dependent chunks and symbols through foreign-key cascade. The
source graph is rebuilt from persisted parser facts with unique fingerprints,
so unchanged vectors remain reusable and repeated ingestion stays idempotent.

Retrieval runs vector, Japanese keyword and symbol channels, combines them with
Reciprocal Rank Fusion and expands matched symbols through relations and
documentation links. The deep profile applies the local memory model as a
bounded evidence reranker. Codex receives only the resulting governed evidence
and citations.

`read-only-analysis` selects the read-only sandbox. Executor selects workspace-write. Version 0.6.0 uses app-server approval policy `untrusted` when the persistent approval callback is configured. Command Policy Engine allows mechanical verification commands, denies destructive patterns and pauses other commands for a stored decision.

### Self-improvement candidate profile

`self-improvement-candidate` creates one directory under the configured self-improvement output root for the current Task. Only that directory is added to the app-server runtime workspace roots. Developer instructions require candidate files and a learning receipt and prohibit formal installation. See [self-improvement.md](self-improvement.md).

### Enterprise knowledge plane

Knowledge Sources bind to a Project and either its Tenant or ProductVersion. Ingestion reads approved local text files, scans and redacts secrets, creates encrypted chunks, requests 1024 dimensional embeddings from Ollama and stores them in PostgreSQL with pgvector.

Local-directory and network-share connectors use a breadth-first directory
queue. Only the current directory is open for enumeration. Its child
directories are queued in stable name order, its supported files are processed,
and the handle is closed before the next directory starts. Durable
`knowledge.collection.progress` events expose the relative directory,
directories scanned, directories pending, files discovered and files
processed. An ingestion-state gate provides single-flight execution for each
source, so repeated API calls follow the active ingestion without launching a
second collector.

Task retrieval uses tenant and product version filters before reciprocal rank fusion. CAG injects only approved, non-instructional evidence blocks into Codex developer instructions and records citation IDs without logging their plaintext. Completed Tasks can create encrypted MemoryCandidates through the local memory model.

Indexing and task feedback remain CAG-owned SSE streams. Frontends never connect to Ollama or Codex app-server directly.

The durable source scheduler polls persisted `next_sync_at` values. It claims
one due source with `FOR UPDATE SKIP LOCKED` and an expiring database lease,
creates a normal ingestion record with trigger `scheduled`, and runs the same
collection and indexing path used by the manual API. Successful runs compute
the next interval. Failed runs retain the error and schedule bounded
exponential retry. Startup recovery closes queued or running ingestions left by
an interrupted process.

## 5. Data identity

Every business record has an independent UUID physical ID.

* `Project.code` is a unique business identifier.
* `Conversation.project_id` references `Project.id`.
* `Conversation.codex_thread_id` stores one opaque runtime thread identity.
* `Task.project_id` references `Project.id`.
* `Task.conversation_id` references `Conversation.id`.
* `Task.id` is also the external Trace ID.
* `Task.client_id` and `Task.idempotency_key` form the idempotent request identity.
* `TaskEvent.task_id` references `Task.id`.
* `TaskEvent.global_sequence` is unique across the Gateway deployment.
* Conversation TaskEvents also store `conversation_id` and a Conversation-local sequence.
* `KnowledgeSource.id` owns sync policy, lease, source health and all ingestion history.
* `KnowledgeIngestion.id` records one manual or scheduled source snapshot comparison.

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

At startup, CAG closes tasks left in a nonterminal state by a prior process.
The task receives a durable `task.failed` event with reason `gateway_restart`.
Related Harness and Agent runs are marked `interrupted`. This keeps
Conversation submission and SSE history consistent after a local restart.

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
* Gateway listens on every IPv4 interface by default. Codex app-server remains a private local child process or loopback service.
* Caller authentication and project authorization remain production gates. Deployments control the reachable network boundary until those gates are implemented.

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

## 11. Self learning and capability governance

Task outcomes produce durable LearningSignal records. Three matching successful
patterns or two matching failure patterns create a content-addressed candidate.
The candidate is stored in the Gateway capability registry with declared
schemas, permissions, dependencies, evidence, acceptance and rollback.

## 12. Managed knowledge source connectors

KnowledgeSource is the governed configuration record for local directories,
Windows UNC shares, Git, GitLab and SVN. Its physical UUID owns ingestion
history, documents and managed snapshots. A normalized source key prevents one
Project from registering the same type, location, reference, subpath and scope
twice.

Git and SVN connectors resolve a revision before copying content into the
Gateway source cache. The immutable snapshot feeds one extractor and cleaning
pipeline. Local and network directories use the same downstream pipeline.
Source content therefore reaches vector storage through a single security,
deduplication and citation boundary.

Credential metadata remains in the source row while the password or token stays
in the operating system credential store. Normal registry and ingestion APIs
return only `credential_configured`. Source editing uses a separate explicit
credential reveal action with private no-store response headers. The frontend
masks the value until the operator requests display.

The ingestion event sequence is:

```text
collection
  |
cleaning and secret scan
  |
incremental comparison
  |
embedding and indexing
  |
encrypted Source Memory persistence
```

The frontend follows the durable ingestion SSE. Page display limits never
truncate backend history.

Scheduled source maintenance uses this durable control loop:

```text
due source
  |
database row lock and expiring lease
  |
normal ingestion event stream
  |
source snapshot and idempotent comparison
  |
persist history and content change timestamp
  |
next interval or retry time
```

The Promotion Service is the only component allowed to change registry state:

```text
proposed
  |
validated
  |
benchmarked
  |
shadow
  |
canary
  |
active
```

The service records every evaluation and transition. Activation changes only
the current Gateway registry. Formal Codex Skills, AGENTS.md files and other
Gateway deployments remain outside this authority.

The four Gardeners inspect documentation, Skill, Tool and Memory assets for
drift and low value. Their findings and actions are persistent records.
