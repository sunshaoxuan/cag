# Agent Gateway API

Base path: `/api/v1`

Current version: `0.5.0`

## Conventions

* JSON timestamps use UTC ISO 8601.
* Resource IDs are UUID strings.
* Task event sequences start at 1 and increase by 1 per task.
* Error responses use FastAPI's standard `detail` field.
* Task creation returns HTTP 202.

## Health

### `GET /health/live`

Confirms that the process can serve requests.

Response:

```json
{
  "status": "ok",
  "service": "agent-gateway",
    "version": "0.5.0"
}
```

### `GET /health/ready`

Checks database connectivity.

## Projects

### `GET /api/v1/projects`

Returns every valid YAML-configured project:

```json
[
  {
    "id": "6ee71a6a-f30a-4a2d-a281-309c7511b832",
    "code": "cag",
    "name": "Codex/ChatGPT Agent Gateway",
    "default_branch": "master",
    "default_runtime_profile": "general-engineering",
    "allowed_runtime_profiles": [
      "general-engineering",
      "read-only-analysis",
      "ci-repair",
      "self-improvement-candidate"
    ]
  }
]
```

### `GET /api/v1/projects/{project_reference}`

Accepts a Project physical UUID or business Code. Unknown references return HTTP 404.

## Create task

Task creation accepts `knowledge_mode` with `off`, `assist` or `required`.
`assist` records an explicit warning and continues when knowledge is unavailable.
`required` ends before Codex execution when approved knowledge retrieval cannot run.

## Enterprise knowledge

* `GET /api/v1/knowledge/status`
* `POST /api/v1/knowledge/sources`
* `GET /api/v1/knowledge/sources`
* `POST /api/v1/knowledge/sources/{source_id}/ingest`
* `GET /api/v1/knowledge/ingestions/{ingestion_id}`
* `GET /api/v1/knowledge/ingestions/{ingestion_id}/events`
* `POST /api/v1/knowledge/search`
* `GET /api/v1/memory-candidates`
* `POST /api/v1/memory-candidates/{candidate_id}/{action}`

Memory actions are `approve`, `reject`, `promote` and `deprecate`.
Product promotion is accepted only for an approved candidate.

## Conversations

### `POST /api/v1/conversations`

Creates the durable CAG conversation that owns frontend continuity, event ordering and the internal Codex thread mapping.

```json
{
  "project_id": "cag",
  "title": "持续工程会话"
}
```

Response:

```json
{
  "id": "UUID",
  "project_id": "UUID",
  "project_code": "cag",
  "title": "持续工程会话",
  "codex_thread_id": null,
  "created_at": "ISO-8601"
}
```

`codex_thread_id` is null until the first successful Task. It is an opaque internal runtime identity and contains no credential material.

### `GET /api/v1/conversations/{conversation_id}`

Returns the Conversation and its current Codex thread identity.

### `GET /api/v1/conversations/{conversation_id}/tasks`

Returns all turns in creation order. Each turn is represented by a Task.

### `GET /api/v1/conversations/{conversation_id}/events`

Keeps one CAG-owned SSE stream open across multiple Tasks in the same Conversation.

Query parameters:

* `after_sequence`: last received Conversation event sequence, default `0`.
* `follow`: keep the stream open, default `true`.

CAG emits a heartbeat comment every 15 seconds while the Conversation is idle. The SSE `id` is the Conversation event sequence. Reconnecting clients may send `Last-Event-ID`; CAG resumes after the greater value from that header and `after_sequence`.

Payload:

```json
{
  "event_id": "UUID",
  "conversation_id": "UUID",
  "task_id": "UUID",
  "sequence": 9,
  "task_sequence": 1,
  "type": "task.created",
  "timestamp": "ISO-8601",
  "data": {}
}
```

`sequence` is continuous across the whole Conversation. `task_sequence` restarts at 1 for each Task.

## Create task

### `POST /api/v1/tasks`

Minimal request:

```json
{
  "project_id": "cag",
  "prompt": "检查当前构建失败的原因，修复能够确认的问题并运行测试。"
}
```

`project_id` accepts a UUID physical ID or a project Code. A Code is resolved to a Project record and strong references store its UUID.

Optional fields:

* `conversation_id`
* `runtime_profile`

For continuous dialogue, `conversation_id` is required by the caller contract. A Task without it remains a one-turn execution and its Codex thread is ephemeral.

Response:

```json
{
  "id": "UUID",
  "project_id": "UUID",
  "project_code": "cag",
  "conversation_id": null,
  "prompt": "检查当前构建失败的原因，修复能够确认的问题并运行测试。",
  "runtime_profile": "general-engineering",
  "status": "queued",
  "final_report": null,
  "error": null,
  "workspace_id": null,
  "workspace_commit": null,
  "created_at": "ISO-8601",
  "started_at": null,
  "completed_at": null
}
```

The supported CAG runtime profiles currently include:

* `general-engineering`
* `read-only-analysis`
* `ci-repair`
* `self-improvement-candidate`

The selected profile must appear in the Project YAML `allowed_profiles`. `self-improvement-candidate` adds one task-specific candidate output directory and injects candidate receipt requirements. It does not install a Skill.

## Get task

### `GET /api/v1/tasks/{task_id}`

Returns the current task status and final report.

Unknown task IDs return HTTP 404.

When workspace preparation succeeds, `workspace_id` has the form `{project_physical_id}/{task_id}` and `workspace_commit` contains the cloned `HEAD` SHA. The host filesystem path is not returned.

## Stream events

### `GET /api/v1/tasks/{task_id}/events`

Content type: `text/event-stream`

Query parameters:

* `after_sequence`: last received event sequence, default `0`.
* `follow`: continue polling until the task reaches a terminal state, default `true`.

SSE example:

```text
id: 1
event: task.created
data: {"event_id":"...","task_id":"...","sequence":1,"type":"task.created","timestamp":"...","data":{}}
```

Reconnecting clients pass the last received sequence through `after_sequence`.

The Phase 2 Fake Runtime happy path emits:

```text
task.created
task.started
workspace.preparing
workspace.ready
agent.plan
agent.message
test.completed
task.completed
```

The local Codex runtime additionally emits event types derived from app-server notifications:

```text
runtime.connected
runtime.thread
agent.plan
agent.plan.delta
agent.message.started
agent.message.delta
agent.message
command.started
command.output.delta
command.completed
agent.reasoning.summary.delta
file.changed
approval.requested
approval.resolved
```

Delta payloads preserve the app-server item and turn identity:

```json
{
  "item_id": "item-id",
  "turn_id": "turn-id",
  "delta": "新增文本"
}
```

`agent.message.delta` also contains `text`, the cumulative text for the current message item. A reconnecting frontend should replace its live projection with `text` and use the completed `agent.message` or `task.completed` event as the authoritative final value.

`command.output.delta` contains exact permitted command output chunks. `agent.reasoning.summary.delta` contains the app-server reasoning summary intended for clients. Hidden reasoning text, credentials and unsupported raw notifications are not part of the CAG API.

`runtime.connected` contains the runtime provider and authentication type. It never contains tokens, credential paths or account email.

`runtime.thread` records `started` for the first Conversation turn and `resumed` for later turns. The frontend receives this event through CAG SSE.

## Planned endpoints

The source specification also requires cancellation, approvals, changes, artifacts and durable Skill proposal records. Their status is tracked in [requirements-matrix.md](requirements-matrix.md).
