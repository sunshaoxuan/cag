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

## Production deployment

The release was subsequently deployed through the managed Windows task on
2026-07-30.

* one active interactive task was allowed to complete before shutdown;
* active Task, ingestion and queue counts were all zero at the cutover gate;
* a 1,743,713,587-byte PostgreSQL custom-format backup was created;
* Alembic advanced from `20260729_0014` to `20260730_0015`;
* managed restart completed in 43.8 seconds;
* Gateway returned `0.18.0` from `0.0.0.0:8000`;
* 21,772 documents and 170,807 vector chunks remained after migration;
* both new file-size columns reported PostgreSQL `bigint`;
* the 5173 container was healthy and browser console error collection was empty;
* `192.168.20.54:8000` returned 0.18.0 and `192.168.20.54:5173` returned HTTP 200.

The Ollama container had been explicitly stopped before release. It was started
after this was detected. Knowledge status then reported Ollama 0.23.3,
`qwen3-embedding:8b`, `qwen3:14b`, 1024 dimensions and a running scheduler.

One scheduled source attempted ingestion during the brief Ollama-unavailable
window and received a bounded connection error. Its persisted retry time
remained active and produced a new queued ingestion at the due time. Another
source continued a normal 0.18.0 scan and wrote durable source entries and
file-level outcomes without interrupting the service.
