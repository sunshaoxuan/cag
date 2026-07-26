# Agent Gateway API

Base path: `/api/v1`

Current version: `0.1.0`

## Conventions

* JSON timestamps use UTC ISO 8601.
* Resource IDs are UUID strings.
* Task event sequences start at 1 and increase by 1 per task.
* Error responses use FastAPI's standard `detail` field in Phase 1.
* Task creation returns HTTP 202.

## Health

### `GET /health/live`

Confirms that the process can serve requests.

Response:

```json
{
  "status": "ok",
  "service": "agent-gateway",
  "version": "0.1.0"
}
```

### `GET /health/ready`

Checks database connectivity.

## Create task

### `POST /api/v1/tasks`

Minimal request:

```json
{
  "project_id": "ohr-back",
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
  "project_code": "ohr-back",
  "conversation_id": null,
  "prompt": "检查当前构建失败的原因，修复能够确认的问题并运行测试。",
  "runtime_profile": "general-engineering",
  "status": "queued",
  "final_report": null,
  "error": null,
  "created_at": "ISO-8601",
  "started_at": null,
  "completed_at": null
}
```

## Get task

### `GET /api/v1/tasks/{task_id}`

Returns the current task status and final report.

Unknown task IDs return HTTP 404.

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

## Planned endpoints

The source specification also requires conversations, cancellation, approvals, changes, artifacts and Skill proposals. Their status is tracked in [requirements-matrix.md](requirements-matrix.md). They are intentionally absent from Phase 1.
