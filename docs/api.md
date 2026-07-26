# Agent Gateway API

Base path: `/api/v1`

Current version: `0.2.0`

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
  "version": "0.2.0"
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
    "default_runtime_profile": "general-engineering"
  }
]
```

### `GET /api/v1/projects/{project_reference}`

Accepts a Project physical UUID or business Code. Unknown references return HTTP 404.

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

## Planned endpoints

The source specification also requires conversations, cancellation, approvals, changes, artifacts and Skill proposals. Their status is tracked in [requirements-matrix.md](requirements-matrix.md).
