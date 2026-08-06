# ADR 0018: PostgreSQL authoritative queue with Redis wake notifications

## Status

Accepted for version 0.17.0 and amended by ADR 0025 for version 0.23.0.

## Context

Agent tasks and knowledge ingestions previously depended on in-process
background execution. Process restarts could leave accepted work without a
claimable owner. Multiple users also require independent Conversation
concurrency, while each Conversation must preserve task order.

## Decision

PostgreSQL stores every queue item, lease, attempt, cancellation request and
worker heartbeat. Interactive Agent tasks and knowledge ingestions have
separate worker pools in a process isolated from the API. Workers claim eligible rows with row locks and
`SKIP LOCKED`.

Redis Pub/Sub sends wake notifications. It contains no authoritative payload.
Workers continue polling PostgreSQL when Redis is unavailable.

Tasks sharing a Conversation are serial. The claim query excludes a task while
an earlier queue item in that Conversation remains queued or leased. Tasks in
different Conversations can run concurrently.

Startup requeues expired leases and active resources that have no usable queue
item. Existing task workspaces are validated and reused for a recovered
attempt.

The Windows launcher also runs the guarded legacy SQLite cutover after Alembic.
It blocks while the source contains active work, replaces target application
tables in one transaction, verifies physical IDs and vectors, and records a
database receipt. The legacy source remains available as offline evidence.

## Consequences

Accepted work survives Gateway restart and Redis failure. Queue capacity and
ownership are observable through the API and online documentation page.
PostgreSQL availability remains a startup requirement.

Per-file knowledge parallelism remains governed by ADR 0015 and requires a
separate work-item schema.

## Validation

Unit and API tests cover claim ordering, completion, cancellation, expired
leases, Redis fallback, migration replacement and Alembic upgrade. Release
validation includes real PostgreSQL and Redis, an isolated Gateway, the
production frontend build and browser evidence.

## Rollback

Stop 0.17.0 workers, retain PostgreSQL and migration receipts, then deploy the
previous release against a compatible database snapshot. Keep the legacy
SQLite source unchanged for forensic comparison.
