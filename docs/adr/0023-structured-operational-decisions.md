# ADR 0023: Structured operational decisions and fail-closed approval

Status: Accepted for 0.22.0

Date: 2026-07-31

## Context

The first issue-center release retained complete Agent reports and runtime
events. Those records supported audit and forensic investigation. Reviewers
still had to infer the problem, improvement route, proposed changes and
acceptance criteria from large nested reports. A Review could also contain an
explicit revision recommendation while a separate heuristic exposed approval.

The management decision requires two separate records:

1. a compact, structured decision brief used for review and approval;
2. complete immutable evidence used for traceability.

## Decision

Planning and independent Review return strict Pydantic schemas. The planner
records problem, impact, root cause confidence, improvement goal, implementation
route, proposed changes, validation, rollback, administrator actions and
responsibility boundary. The reviewer records its recommendation, blocking
findings, required changes, conditions and validation additions.

The implementation route is one of:

* `agent_self_improvement`
* `human_code_change`
* `external_operator_action`
* `mixed`
* `out_of_scope`
* `undetermined`

Approval is available only when both structured objects are valid, the Review
recommends `approve`, and the blocker list is empty. Every other supported
internal case enters `plan_revision_required`. The approval endpoint repeats
the same checks to prevent a UI bypass.

The management page renders the decision brief first. Versioned artifacts and
the event timeline remain complete and collapsed by default.

Issue event ordering uses an atomic counter stored on the issue row. Concurrent
writers receive distinct sequence values without calculating a shared maximum.

## Migration

Alembic revision `20260731_0018` adds the decision fields and backfills an
initial implementation route from the stored responsibility boundary. Historical
waiting-approval records whose Review evidence explicitly requires revision
move to `plan_revision_required`.

## Consequences

Administrators receive a comparable decision record across issues. Raw evidence
remains available for audit. Invalid AI output pauses the workflow for revision.
Internal classification still requires administrator approval before a
self-improvement task can be created.

## Rollback

Export the operational issue tables when decision history must be retained.
Revert the 0.22.0 release and downgrade Alembic to `20260731_0017`. Historical
artifacts remain valid at the older schema, while the added decision fields are
removed by the downgrade.
