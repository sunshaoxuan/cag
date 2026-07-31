# Version 0.21.0 final receipt

## Scope

Governed self-operations issue intake, AI boundary classification, planning,
independent Review, administrator approval, isolated implementation,
evaluation, reopening and closure.

## Validation status

Implementation and isolated validation are complete. The backend, PostgreSQL
and pgvector, supervisor, frontend and browser gates passed. The production
0.20.0 service remained available during validation.

## Approval guarantee

The issue center records and analyzes failures automatically. It does not
start an internal code improvement task until an administrator approves the
reviewed proposal. External and credential issues wait for recorded
remediation evidence. Evaluation evidence controls closure and failed
evaluation returns the issue to another governed cycle.

## Rollback

Restore the pre-release PostgreSQL custom-format backup in an isolated
database, validate row and vector counts, stop the managed task, point the
ignored local configuration to the verified restored database and start the
managed task. Revert the release commit if the application files also require
rollback.
