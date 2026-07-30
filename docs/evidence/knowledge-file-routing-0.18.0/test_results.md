# Test results

## Backend

`python -m pytest` collected 110 tests.

* 108 passed
* 2 skipped because optional PostgreSQL URLs are not set in the default suite
* total coverage 85.57 percent
* required threshold 85 percent

The focused knowledge, migration and code intelligence group passed 32 tests.

## PostgreSQL and pgvector

A fresh isolated database upgraded from the first Alembic revision through
`20260730_0015`.

* `knowledge_source_entries.file_size` is `bigint`
* `knowledge_ingestion_rejections.file_size` is `bigint`
* native pgvector storage and search test passed, 1 passed

The first repeated test attempt used prior encrypted rows from a different
temporary key and failed with `InvalidTag`. The isolated database was recreated,
all migrations were applied, and the test passed. Production data was not
involved.

## Frontend

* 12 component tests passed
* TypeScript build passed
* Vite production build passed
* isolated browser page showed `v0.18.0`
* source summary showed 5 assets, 1 code, 2 documents and 2 metadata-only
* ZIP and database dump rows showed metadata-only reasons
* code row showed structural code analysis
* browser console error collection was empty

## Runtime boundary

Validation used loopback-only ports 8018 and 5180 and a task-specific SQLite
database for the UI fixture. The current production processes on ports 8000 and
5173 remained running and were not replaced.
