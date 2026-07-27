# Governed Agent Harness

## Scope

Version 0.6.0 adds an orchestration plane around the locally authenticated Codex runtime. CAG owns the task contract, workspace permissions, child run records, event ordering, approvals, artifacts and validation evidence.

## Profiles

| Profile | Investigation | Execution | Review |
|---|---|---|---|
| `single` | none | one Executor | runtime validation |
| `fast` | Repository Mapper | one Executor | one Validator |
| `balanced` | three parallel read-only investigators | one Executor | code, security and validation reviews |
| `deep` | three parallel read-only investigators | one Executor | code, architecture and citation reviews |

The configured concurrency ceiling is three. Each investigator receives an independent Git clone and a read-only Codex sandbox. Executor receives the task workspace with write permission. Reviews start after Executor completes and use read-only access.

Investigator and reviewer runs have a bounded five minute budget and explicit
command and output limits. Executor keeps the configured task budget. This
prevents broad repository dumps and repeated searches from consuming the full
implementation window.

## Structured exchange

Each AgentRun has a physical UUID and emits a structured report. The report is persisted as an AgentArtifact with a schema version and SHA 256 content hash. Synthesizer context contains report summaries and evidence requirements. Hidden reasoning is outside the interchange contract.

## Unified events

CAG assigns the authoritative sequence through TaskEvent. Child runtime events contain `agent_run_id` and `role`. Harness lifecycle events are:

* `harness.started`
* `harness.preflight.completed`
* `agent.run.queued`
* `agent.run.started`
* `agent.run.completed`
* `agent.run.failed`
* `harness.synthesis.completed`
* `harness.completed`

The frontend may filter these events. The backend retains every persisted event and supports SSE resume.

## Command policy and approval

Command Policy Engine classifies requests as `allow`, `approval_required` or `deny`. Read and verification commands are mechanically allowed. Destructive patterns are denied. An unknown command in a read-only Harness sandbox is recorded and allowed by the permission intersection. An unknown Executor command creates a persistent ApprovalRequest and places the Task in `waiting_approval` until a user decision or timeout.

The app-server approval callback receives the resolved decision. File edits are assigned only to Executor. Effective permission is the intersection of app-server sandbox, Harness role and command policy.

CAG emits `approval.pending` immediately after persistence. The frontend lists
the command, risk level and approval ID and allows an operator to approve or
deny it while the Agent remains suspended.

## Evidence and limits

The deterministic suite validates parallel scheduling, Artifact persistence, quality records, policy classification and approval resolution without consuming Codex quota. Real three-process Codex validation is recorded separately because it consumes the local subscription runtime.
