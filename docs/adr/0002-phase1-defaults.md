# ADR 0002: Phase 1 execution and persistence defaults

Status: Accepted

Date: 2026-07-27

## Context

Phase 1 needs a runnable Task API without production repositories, production databases, MCP servers or external model consumption.

## Decision

* Use FastAPI and synchronous SQLAlchemy 2 sessions.
* Use PostgreSQL 16 in Docker Compose.
* Use SQLite for local development and isolated tests.
* Use Alembic for durable schema migration.
* Use FastAPI background tasks for the Phase 1 executor.
* Use the deterministic Fake Runtime.
* Use polling over committed TaskEvent rows to produce SSE.
* Default runtime profile is `general-engineering`.

## Consequences

The Phase 1 executor is process-local. A service restart can leave a running task incomplete. Phase 2 will introduce a Redis-backed durable queue and recovery scan.

The SSE endpoint is horizontally safe only after event notification and queue coordination are implemented. Database ordering remains authoritative.

## Acceptance

* Unit tests prove deterministic Fake Runtime output.
* API tests prove task creation, query, failure handling and ordered SSE.
* Migration tests prove schema upgrade.
* Docker Compose validation proves a parseable deployment definition.

## Rollback

Disable background execution and keep task creation in `queued`. Data remains compatible with a later durable worker.
