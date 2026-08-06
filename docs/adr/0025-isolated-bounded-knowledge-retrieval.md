# ADR 0025: Isolated bounded knowledge retrieval

## Status

Accepted for 0.23.0.

## Context

CAG 0.22.8 ran API handlers and all durable queue consumers in one process.
Knowledge search loaded every accessible Chunk, CodeSymbol, CodeRelation and
CodeDocumentLink before application-side ranking. A production customer Code
search timed out at 45 and 60 seconds. Health, Task status and cancellation
requests lost responsiveness, and the host supervisor restarted the API.
Expired lease recovery also cleared a pending cancellation marker.

## Decision

The managed host and Compose runtime use an API process plus a durable queue
worker process. PostgreSQL remains the queue authority and Redis remains a
wake-up channel. The API process creates jobs, reports status, streams events
and records cancellation. The worker process owns interactive, knowledge and
operations consumers. Both processes connect to the Redis wake-up channel. The
API publishes admission and cancellation wake-ups without starting local
consumers.

Knowledge search performs indexed PostgreSQL candidate selection with fixed
limits. `fast` uses text and identifier paths. `balanced` adds pgvector Top K.
`deep` adds bounded local reranking. PostgreSQL pg_trgm indexes cover normalized
Chunk text, document paths and Code symbol names. Every profile has an overall
deadline and every PostgreSQL retrieval transaction has statement timeout.

Customer ledger extraction is a dedicated knowledge queue job backed by the
existing physical Task, TaskEvent and QueueItem records. CAG owns its structured
result schema and rejects candidates without authoritative returned Chunk
citations. Candidate IDs are independent physical UUIDs. Extraction first
resolves a customer root directory whose path contains the requested Code,
official name or alias. Section retrieval is restricted to that root. A missing
authoritative root produces a learning gap instead of a corpus-wide fallback.

Cancellation takes precedence over lease requeue. Recovery commits cancelled
state before any new lease can be acquired. Cancelling a scheduled ingestion
also releases its source lease and advances `next_sync_at` by the configured
interval, so the scheduler cannot immediately recreate the cancelled run.
Active work checks cancellation every second. Queue completion compares the
cancel request timestamp with resource completion, so the earlier terminal
decision wins deterministically.

## Consequences

Knowledge CPU, model and database work cannot occupy the API event loop.
Retrieval cost is bounded by candidate limits rather than total corpus rows.
Health, Task, Queue and cancellation APIs remain available during slow work.
Host launch now manages two child processes. Compose includes a separate worker
service. Operational acceptance must verify both process IDs and active worker
heartbeats.

## Rollback

Stop API and worker, restore the prior release commit, run Alembic downgrade to
`20260805_0020`, and restart the prior host launcher. The downgrade removes only
the new pg_trgm indexes. Existing knowledge, tasks and queue rows remain intact.
