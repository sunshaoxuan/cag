# ADR 0022: Governed self-operations issue center

Status: Accepted for 0.21.0

Date: 2026-07-31

## Context

CAG already persisted Task, knowledge ingestion, approval, capability,
evaluation and rollback records. Failure handling remained distributed.
Task-learning signals did not include every knowledge, API, supervisor or
connector failure. Some retries ended with an error record and no governed
improvement cycle.

The operating requirement is that every supported failure can enter one
visible process. CAG must determine its responsibility boundary, prepare and
Review an improvement proposal, wait for administrator authority, evaluate the
result and close only with evidence.

## Decision

CAG adds `OperationalIssue`, `OperationalIssueOccurrence`,
`OperationalIssueArtifact` and `OperationalIssueEvent`.

PostgreSQL remains authoritative. `queue_items.issue_id` adds issue work to the
existing lease, heartbeat, retry and recovery mechanism. Redis remains an
optional wake-up optimization. The `operations` queue receives a separate
Worker pool.

Triage invokes the local ChatGPT-authenticated Codex runtime in a read-only
isolated workspace. One run classifies and plans. A second independent run
reviews architecture, security, migration and regression coverage. Both
outputs become versioned artifacts.

Administrator approval is required before implementation. Internal issues
create a normal durable CAG Task on
`codex/improvement/<issue-code>` with the self-improvement candidate profile and
balanced Harness. The workflow permits local commits and withholds push and
merge authority. External and credential issues wait for administrator
evidence.

Every implementation enters independent evaluation. Passing evaluation closes
the issue. Failed evaluation restores `detected` status and queues another
triage cycle.

## Boundary

The supported boundary classes are:

* `cag_internal`
* `external_dependency`
* `credential_or_authorization`
* `policy_or_scope`

Boundary classification controls the permitted next action and cannot grant
credentials, expand authorization or bypass approval.

## Failure durability

Task and knowledge queue terminal failures are captured automatically.
Unhandled API exceptions are captured by the Gateway boundary. The Windows
supervisor writes failures to a local JSONL spool while the Gateway is
unavailable and submits them after readiness returns. External systems can use
the public intake endpoint with a stable event ID.

## Security

Secret-like keys and values are removed before persistence. Triage, Review and
evaluation receive read-only instructions. Implementation uses an isolated
clone and explicit branch. Every plan, Review, approval, implementation,
evaluation and transition is retained.

## Rollback

Revert the 0.21.0 release and downgrade Alembic to `20260730_0016`. Preserve an
export of the operational issue tables before downgrade when issue history must
remain available. Remove the issue spool only after its events are confirmed in
PostgreSQL.
