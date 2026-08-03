# One Agent Gateway API

Base path: `/api/v1`

Current version: `0.22.5`

The visual online reference is available at `/api-docs`. FastAPI interactive
OpenAPI remains available at `/docs`, and the machine-readable contract is
available at `/openapi.json`.

## Conventions

* JSON timestamps use UTC ISO 8601.
* Resource IDs are UUID strings.
* Task event sequences start at 1 and increase by 1 per task.
* Every TaskEvent also has a Gateway-wide `global_sequence`.
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
    "version": "0.22.5"
}
```

### `GET /health/ready`

Checks PostgreSQL connectivity and the pgvector extension. The response also
returns `backend`, `native_vector_search` and `pgvector_version`.

## Projects

### `GET /api/v1/projects`

Returns every valid YAML-configured project:

```json
[
  {
    "id": "6ee71a6a-f30a-4a2d-a281-309c7511b832",
    "code": "cag",
    "name": "One Agent Gateway",
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
The default `assist` mode applies to every Conversation turn. Retrieval finishes
before Codex app-server starts the turn. The injected evidence contains bounded
knowledge fragments, source identity, canonical path, revision and
`resource_uri`. Task SSE records the citation metadata without publishing the
knowledge plaintext.

## Enterprise knowledge

* `GET /api/v1/knowledge/status`
* `POST /api/v1/knowledge/sources`
* `GET /api/v1/knowledge/sources`
* `PATCH /api/v1/knowledge/sources/{source_id}`
* `DELETE /api/v1/knowledge/sources/{source_id}`
* `POST /api/v1/knowledge/sources/{source_id}/credential/reveal`
* `POST /api/v1/knowledge/sources/{source_id}/validate`
* `POST /api/v1/knowledge/sources/{source_id}/ingest`
* `GET /api/v1/knowledge/sources/{source_id}/ingestions`
* `GET /api/v1/knowledge/sources/{source_id}/entries`
* `GET /api/v1/knowledge/ingestions/{ingestion_id}/rejections`
* `GET /api/v1/knowledge/ingestions/{ingestion_id}/rejections/export`
* `GET /api/v1/knowledge/ingestions/{ingestion_id}/rejections/archive`
* `GET /api/v1/knowledge/ingestions/{ingestion_id}`

## Durable queue

PostgreSQL is authoritative for queue state. Redis Pub/Sub only wakes workers
across processes. A Redis outage increases pickup latency to the configured
poll interval and does not lose accepted jobs.

* `GET /api/v1/queue/status`
* `GET /api/v1/queue/items?queue_name=interactive&status=queued`
* `POST /api/v1/queue/items/{item_id}/cancel`

Interactive Agent tasks and knowledge ingestions use separate worker pools.
Tasks in the same Conversation are claimed in creation order. Tasks belonging
to different Conversations can run concurrently.

The self-operations issue center uses a third `operations` Worker pool.

Example:

```powershell
$status = Invoke-RestMethod `
  -Uri "http://gateway-host:8000/api/v1/queue/status"
$status.queues
$status.workers
$status.redis
```

## Self-operations issue center

Every issue and occurrence has an independent physical UUID. A stable
Project-scoped fingerprint groups repeated failures while
`external_event_id` makes supervisor and connector replay idempotent. Evidence
is sanitized before persistence.

### Intake and query

* `POST /api/v1/operations/issues/intake`
* `GET /api/v1/operations/dashboard`
* `GET /api/v1/operations/issues`
* `GET /api/v1/operations/issues/{issue_id}`
* `GET /api/v1/operations/issues/{issue_id}/events`

Example:

```json
{
  "project_reference": "cag",
  "source_type": "knowledge_ingestion",
  "source_id": "2053dbe5-3ba7-4125-beea-91d5678f7317",
  "title": "Network share authentication failed",
  "error_type": "CredentialFailure",
  "error_message": "Authentication failed",
  "severity": "high",
  "external_event_id": "upds-20260731-001",
  "event_type": "failure",
  "evidence": {
    "knowledge_source_id": "c4837509-0c4c-4689-bb34-e30a1138da05"
  }
}
```

The intake response is HTTP 202. A new or reopened issue enters the
`operations` queue. The local Codex runtime produces a boundary decision,
versioned plan and independent Review in read-only isolated workspaces.
Every triage cycle receives a sequence-addressed workspace cloned from the
current default branch, including cycles started by reopen or failed
evaluation. Prior workspaces remain immutable evidence and are never reused
for a new plan.

Issue list query parameters include `status`, `severity`, `boundary`,
`resolution_mode` and `limit`. `resolution_mode` is one of
`agent_self_improvement`, `human_code_change`, `external_operator_action`,
`mixed`, `out_of_scope` or `undetermined`.

The issue response exposes the compact approval record separately from complete
artifacts:

```json
{
  "code": "OI-6B26534BF5",
  "status": "plan_revision_required",
  "boundary": "cag_internal",
  "resolution_mode": "agent_self_improvement",
  "resolution_mode_confidence": 0.91,
  "resolution_mode_reason": "The bounded change is inside the CAG repository.",
  "review_recommendation": "revise",
  "blocking_finding_count": 2,
  "event_count": 235,
  "allowed_actions": ["reopen", "reject"],
  "planned_actions": ["plan", "review", "request_approval"],
  "decision_brief": {
    "administrator_language": "zh-CN",
    "problem_summary": "Review 证据与审批状态不一致。",
    "impact_summary": "不完整的方案可能被错误展示为可审批。",
    "root_cause_summary": "自由格式报告被宽松规则归纳为批准。",
    "improvement_goal": "使用同一个经过校验的决策对象驱动页面和 API 门禁。",
    "recommended_changes": [
      {
        "area": "问题 Review",
        "change": "解析严格的 Review 结构，并在异常时关闭审批。",
        "reason": "持久化的 Review 结论必须成为唯一审批依据。"
      }
    ],
    "validation_plan": [
      "Review 要求修订时，页面隐藏审批入口，API 拒绝审批。"
    ],
    "blocking_findings": [
      {
        "code": "B1",
        "severity": "high",
        "title": "需要结构化 Review",
        "finding": "当前 Review 不满足审批条件。",
        "required_change": "重新生成有效的独立 Review。"
      }
    ],
    "approval_ready": false
  }
}
```

`decision_brief` is the reviewer-facing projection. `artifacts` retain the
complete plan and Review. Runtime evidence is read from the paginated events
endpoint. Invalid or incomplete
structured output, a `revise` recommendation, or any blocking finding produces
`plan_revision_required`.

`allowed_actions` is the server-authoritative list of management actions
permitted in the current state. The UI must use this field instead of inferring
buttons from `status`. `planned_actions` retains the implementation capabilities
identified by the planner.

The events endpoint returns the newest page in ascending sequence order:

```json
{
  "items": [],
  "total": 235,
  "has_more": true,
  "next_before_sequence": 136
}
```

Use `limit` from 1 to 500 and pass the returned `next_before_sequence` as
`before_sequence` to read the next older page. Issue list and detail polling do
not transfer the complete event history.

`decision_brief.administrator_language` is `zh-CN`. Administrator-facing
summary and decision fields use Simplified Chinese. Code identifiers, commands,
paths, API names and error codes retain their original text.
If the planning runtime fails before producing a plan, the issue enters
`triage_failed` with a Chinese failure brief, one visible blocker and
`approval_ready: false`. The original technical error remains in the root cause
field and collapsed audit evidence.

### Approval and implementation

* `POST /api/v1/operations/issues/{issue_id}/approve`
* `POST /api/v1/operations/issues/{issue_id}/reject`
* `POST /api/v1/operations/issues/{issue_id}/implementations`
* `POST /api/v1/operations/bulk/implementations`

Every mutation in this section, plus evaluation and reopen, requires:

```text
X-CAG-Admin-Token: <configured operations administrator token>
X-CAG-Admin-Identity: <authenticated administrator identity>
```

The token is compared to `AGENT_GATEWAY_OPERATIONS_ADMIN_TOKEN` with a
constant-time comparison. The authenticated identity header is written to the
audit record. Administrator names supplied in a request body are ignored.
Missing configuration returns HTTP 503 and invalid credentials return HTTP
401.

Approval request:

```json
{
  "note": "批准隔离分支实施，并执行规模化检索回归测试"
}
```

The server accepts approval only when `review_recommendation` is `approve`,
`blocking_finding_count` is zero and `decision_brief.approval_ready` is true.
Clients receive HTTP 409 when any gate is unmet.

The administrator can reject a pending, revision-required, triage-failed or
external-action issue. Rejection records the authenticated administrator,
reason and immutable `issue.rejected` event, closes the current cycle and
forbids the proposed modification. A future occurrence or explicit reopen can
start a new audited cycle.

Approved CAG-internal issues create a standard Task with runtime profile
`self-improvement-candidate`, balanced Harness and a
`codex/improvement/<issue-code>` branch. The task can commit locally and cannot
push or merge through this API.

Credential and external dependency issues move to `waiting_external`.
Administrators record manual or batch changes with summary, optional branch,
commit hashes and validation evidence. This queues an independent evaluation.

### Evaluation and continuation

* `POST /api/v1/operations/issues/{issue_id}/evaluations`
* `POST /api/v1/operations/issues/{issue_id}/reopen`

AI evaluation replays the original evidence and checks validation, regression,
performance, security, migration and rollback readiness. Passing evaluation
closes the issue. Failed evaluation queues another triage cycle with all prior
artifacts and events preserved.

Reopen accepts only `closed`, `rejected`, `validation_completed`,
`out_of_scope`, `triage_failed` and `plan_revision_required`. A successful
reopen clears the prior approval, implementation, evaluation and decision
projection, retains immutable occurrences, artifacts and events, and queues one
new triage item. Other states return HTTP 409.

Controlled deployment validation uses `validation_completed`. It remains
auditable and does not create a false administrator rejection record.

AI investigation persists completed messages, commands, tests, state changes,
plans, Reviews and evaluations. Runtime event names ending in `.delta` are
transient delivery projections and are excluded from the durable operational
issue timeline.
* `GET /api/v1/knowledge/ingestions/{ingestion_id}/events`
* `POST /api/v1/knowledge/search`
* `GET /api/v1/memory-candidates`
* `POST /api/v1/memory-candidates/{candidate_id}/{action}`

Memory actions are `approve`, `reject`, `promote` and `deprecate`.
Product promotion is accepted only for an approved candidate.

Knowledge search results and injected citations include `source_name`,
`source_type`, canonical `path`, `source_commit` and `resource_uri`. Local and
UNC resources use `file:` URIs. GitLab and recognized Git web origins use
revision-pinned file links. Other repository origins retain their repository
URI together with revision and path metadata.

Source create accepts local directory, Windows network share, Git, GitLab and
SVN locations. Credential secrets are write only. The complete source schema,
idempotency rules and ingestion SSE event catalog are documented in
`docs/knowledge-source-api.md`.

Source create and patch accept `sync_mode` and `sync_interval_minutes`.
Source responses expose scheduler and health fields. Ingestion responses expose
manual or scheduled trigger, changed and removed file counts, and timestamps.
Credential reveal is a separate explicit POST response with private no-store
headers. Source list, source update and ingestion responses never include the
secret.

Source responses include `entry_summary`, grouped by `processing_mode` and
status. The entries endpoint accepts `limit`, `offset`, `processing_mode`,
`present` and `query`. File sizes are 64-bit integers.

Source responses also include `active_generation_id` and `retrieval_health`.
The health object reports actual total and accessible chunk counts,
legacy-document count and one of `searchable`, `refreshing`, `degraded`,
`indexing`, `scope_mismatch`, `approval_required`, `disabled` or `empty`.
Product scope matches the stable Product physical ID across ProductVersion
changes.

```powershell
$entries = Invoke-RestMethod `
  -Uri "$baseUrl/api/v1/knowledge/sources/$sourceId/entries?limit=100"
$entries.items |
  Select-Object relative_path, processing_mode, status, file_size, reason_code
```

Processing modes are `metadata_only`, `path_only`, `document` and `code`.
Archive, dump, backup, binary and policy-sized files use `metadata_only`.
Their content is not extracted or embedded. Zero-byte files use `path_only`.
Code uses the structural analyzer and does not enter the ordinary document
extraction branch.

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

The API is the primary task entry point. The React page calls this same
endpoint as a test console.

Optional request headers:

* `X-CAG-Client-ID`: stable caller identifier.
* `X-Request-ID`: caller request identifier.
* `X-CAG-Source`: defaults to `external_api`.
* `Idempotency-Key`: deduplicates a request for the same client.

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
  "trace_id": "UUID",
  "project_id": "UUID",
  "project_code": "cag",
  "conversation_id": null,
  "trigger_source": "external_api",
  "client_id": "erp-integration",
  "client_request_id": "erp-request-001",
  "request_hash": "SHA256",
  "events_url": "/api/v1/tasks/UUID/events",
  "audit_url": "/api/v1/audit/tasks/UUID",
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

The response headers expose `X-CAG-Trace-ID`,
`X-CAG-Idempotent-Replay` and `Location`. Replaying the same request with
the same client and idempotency key returns the existing Task. Reusing the key
for a different request returns HTTP 409.

When knowledge is injected, a completed `final_report` adds
`knowledge_citations`. Each citation contains `chunk_id`, `source_id`,
`source_name`, `source_type`, `path`, `resource_uri`, `scope`, `commit` and
retrieval `score`. The preceding `knowledge.context.injected` SSE event carries
the same citation objects, so an SSE client can associate the answer with its
original resources without receiving the knowledge plaintext.

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
data: {"event_id":"...","task_id":"...","sequence":1,"global_sequence":42,"type":"task.created","timestamp":"...","data":{}}
```

Reconnecting clients pass the last received sequence through `after_sequence`.

## API audit

### `GET /api/v1/audit/tasks`

Returns recent API call traces. Filters are `trigger_source`, `client_id`,
`status` and `limit`.

### `GET /api/v1/audit/tasks/{task_id}`

Returns the durable request identity, request metadata, event count, last global
sequence, final report and error for one Trace ID.

### `GET /api/v1/audit/events`

Keeps one Gateway-wide SSE open for every task action. Each SSE event is named
`audit.event`; the JSON field `type` preserves the original TaskEvent type.

Query parameters:

* `after_sequence`
* `follow`
* `trigger_source`
* `client_id`
* `task_id`

`Last-Event-ID` and `after_sequence` support standard resumption. The payload
includes the Trace ID, global sequence, task sequence, source, client identity,
project and original event data. See
[external-api-observability.md](external-api-observability.md).

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
approval.pending
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

## Capability governance

The Gateway exposes:

```text
GET  /api/v1/capabilities/skills
POST /api/v1/capabilities/skills
GET  /api/v1/capabilities/tools
POST /api/v1/capabilities/tools
GET  /api/v1/capabilities/validators
GET  /api/v1/capabilities/harness-profiles
GET  /api/v1/evaluations
POST /api/v1/evaluations/{asset_id}
GET  /api/v1/promotions
POST /api/v1/promotions/{asset_id}/shadow
POST /api/v1/promotions/{asset_id}/canary
GET  /api/v1/rollbacks
POST /api/v1/rollbacks/{asset_id}
POST /api/v1/gardeners/run
GET  /api/v1/standards/controls
```

Capability proposals declare a trigger, input and output schemas, permissions,
dependencies, timeout, evidence requirements, acceptance and rollback. A
proposal remains inactive until the complete evaluation, shadow and canary
state machine succeeds.

Task SSE includes `learning.capture.started`, `learning.signal.recorded`,
`learning.candidate.proposed`, `learning.capture.completed` and
`learning.capture.failed`. CAG persists every event before projecting it to the
frontend.

## Code knowledge

### Search knowledge

`POST /api/v1/knowledge/search`

The request accepts `project_id`, `query`, `limit` and `profile`. Profile values
are `fast`, `balanced` and `deep`. All profiles combine vector, Japanese keyword
and exact code-symbol channels. Symbol matches expand through resolved code
relations and deterministic documentation links. `deep` additionally asks the
local `qwen3:14b` model for JSON constrained evidence scores. Provider failure
falls back to the deterministic Reciprocal Rank Fusion order.

Each result includes `match_reasons` and `symbol_ids` in addition to chunk,
source, path, score, scope and source revision. Possible reasons include
`vector`, `japanese_keyword`, `code_symbol`, `code_relation`,
`code_document_link` and `local_reranker`.

### Code summary

`GET /api/v1/knowledge/code/summary?project_id={project_id}`

Returns accessible symbol, relationship, documentation-link and unresolved
relationship counts plus language and symbol-kind distributions.

### Code symbols

`GET /api/v1/knowledge/code/symbols`

Query fields are `project_id`, optional `query`, optional `kind` and `limit`.
The text filter matches symbol name, qualified name and canonical path.

`GET /api/v1/knowledge/code/symbols/{symbol_id}?project_id={project_id}`

Returns the symbol location, signature, parser, diagnostics, outgoing and
incoming relations and linked-document evidence. Project resolution, approved
source status and Tenant or ProductVersion scope are required for every code
knowledge endpoint.

The ingestion SSE adds `knowledge.code.analysis.completed` and
`knowledge.code.graph.persisted`. Their data reports code-file, parser, symbol,
relationship and documentation-link counts. The facts remain in the complete
backend event sequence even when the frontend displays fewer events.
