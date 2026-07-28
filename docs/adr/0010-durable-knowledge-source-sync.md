# ADR 0010: Durable knowledge source synchronization

## Status

Accepted for version 0.10.0.

## Context

Managed sources, ingestion history and indexed knowledge were already
persistent. A new ingestion existed only after an API or web user pressed the
manual collection action. Long lived folders and repositories need repeated
observation because files, revisions and deletions change after the first
indexing run.

The indexing path already compares canonical path and cleaned content hash.
That comparison can support a durable control loop without generating duplicate
documents or vectors.

## Decision

`KnowledgeSource` stores one explicit sync policy:

* `manual` keeps the source registered and waits for an API action.
* `scheduled` stores an interval and a durable next due time.

A Gateway scheduler polls due rows. It uses a row lock with an expiring lease
before creating a scheduled `KnowledgeIngestion`. The ingestion executes the
same collection, cleaning, vector indexing and Source Memory pipeline used by a
manual request.

Every run records its trigger, started and completed time, files seen, files
changed, paths removed, unchanged paths, vectors reused and error. Successful
runs set the next regular interval. Failed runs use bounded exponential retry.
Startup recovery closes interrupted runs so a later lease can safely retry.

Existing sources migrate to manual mode. The management page defaults new
sources to scheduled mode and allows operators to opt into automatic processing
for earlier records.

## Consequences

The source list is the long term system of record for configured knowledge
locations and source health. Complete rescanning detects deletions and remote
revision changes. Hash based incremental indexing keeps embedding work
proportional to actual changes.

Database leases support multiple polling Gateway Workers. Lease duration must
cover the normal ingestion window. An expired lease permits recovery from a
dead Worker. All Workers continue to share the existing Ollama serialization
guard.

## Verification

Acceptance requires:

* two Workers cannot claim one unexpired lease
* source additions, changes and deletions produce correct incremental counts
* unchanged documents retain vectors
* failures persist an error and a retry time
* every scheduled run remains queryable through the source history API
* Alembic upgrade and downgrade preserve the expected schema boundary
* the management page displays scheduler state and persisted run history

## Rollback

Set `AGENT_GATEWAY_KNOWLEDGE_SCHEDULER_ENABLED=false` to stop scheduled claims
while retaining source policies and history. Change individual sources to
`manual` for a narrower rollback. Alembic downgrade to `20260728_0009` removes
the scheduling columns after application rollback and database backup.
