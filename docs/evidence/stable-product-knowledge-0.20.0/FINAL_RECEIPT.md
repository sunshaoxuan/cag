# Version 0.20.0 final receipt

## Scope

Stable product knowledge retrieval, processor-upgrade reprocessing, atomic
knowledge refresh behavior and truthful retrieval health.

## Status

Implementation and release validation are complete. The backend suite,
frontend suite and production build passed. SQLite and isolated PostgreSQL
migration round trips passed. Browser acceptance confirmed the retrieval health
panel with zero console errors.

The current 0.18.0 production process was left running throughout validation.
Version 0.20.0 becomes active when the managed service performs its next
approved restart and migration.

## Rollback

Revert the 0.20.0 release commit and downgrade PostgreSQL to
`20260730_0015`. Existing vectors remain intact.
