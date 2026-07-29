# ADR 0016: PostgreSQL pgvector managed runtime cutover

## Status

Accepted for version 0.15.0. Live cutover is deferred until the current
long-running knowledge ingestion reaches a terminal state.

## Context

The Compose topology already included PostgreSQL 16 with pgvector, while the
Windows host launcher created a SQLite runtime database when no connection URL
was present. Knowledge embeddings were stored as JSON in that compatibility
database. Retrieval loaded candidate vectors into the application and computed
cosine similarity in Python.

This split made the declared deployment architecture different from the live
managed runtime. It also prevented PostgreSQL row leases, native vector indexes
and later parallel work queues from becoming a reliable system boundary.

## Decision

Every managed and development runtime uses PostgreSQL 16 with pgvector.
SQLite is allowed only when the application environment is `test` and the
isolated-test flag is enabled. The one-time migration reader can open the
legacy source in read-only mode.

The readiness gate verifies:

1. PostgreSQL connectivity.
2. Presence of the `vector` extension.
3. Native vector search capability.

The embedding column remains `vector(1024)`. PostgreSQL orders the vector
retrieval channel with cosine distance operator `<=>`. The existing HNSW index
uses `vector_cosine_ops`.

The Windows launcher has no SQLite fallback. Database credentials remain in an
ignored environment file or operating-system environment. PostgreSQL is
published only on `127.0.0.1:5432` for the trusted host Gateway.

## Migration safety

The migration source must pass SQLite integrity checking and contain no queued
or running ingestion. Dry run is the default. Apply requires an explicit
switch.

The migration uses a consistent temporary SQLite backup, copies tables in
foreign-key order inside one PostgreSQL transaction, preserves UUID physical
IDs and removes the temporary snapshot after completion. The target must be at
Alembic revision `20260729_0013`. All ordinary target tables must be empty. The
known Alembic audit-cursor bootstrap row is replaced inside the same
transaction.

The receipt records:

* source file SHA 256;
* source integrity and active-ingestion check;
* source and target table counts;
* ordered physical-ID digests;
* source and target vector counts;
* target vector dimensions;
* pgvector version and HNSW index presence.

The service switches only after the receipt passes. The old SQLite database is
retained offline as a read-only rollback artifact and is excluded from runtime
configuration.

## Consequences

Vector storage and vector ranking use the professional database boundary.
Resumable workers can rely on PostgreSQL locking and leases in the next
implementation phase. Local unit tests remain fast and isolated.

The current learning task cannot be migrated in place. Its existing process
continues until completion, followed by the controlled migration and service
cutover.

## Rollback

Stop the PostgreSQL-backed Gateway, preserve the failed target database and its
receipt, and restore the archived pre-cutover application version with the
read-only SQLite source copied back to its former managed location. Record the
rollback before allowing new knowledge ingestions.
