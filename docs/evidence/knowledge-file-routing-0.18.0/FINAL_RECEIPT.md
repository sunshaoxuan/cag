# Version 0.18.0 final receipt

## Delivered

* durable file and directory asset inventory with UUID identities;
* metadata-only policy for archives, dumps, backups, binaries and oversized
  files;
* path-only knowledge for zero-byte files;
* hard structural code-analysis routing;
* processor-policy fingerprints and legacy code backfill;
* 64-bit PostgreSQL file-size fields;
* source asset API, management table and compact error presentation;
* online API example, architecture, deployment, ADR and requirement updates.

## Acceptance

Backend, frontend, Alembic, native pgvector and isolated browser checks passed.
The screenshot is stored at
`docs/evidence/screenshots/knowledge-file-inventory-detail-0.18.0.png`.

## Cutover

The live managed service was upgraded on 2026-07-30 after all active work
reached a terminal state. PostgreSQL was backed up before shutdown. Alembic
revision `20260730_0015`, Gateway 0.18.0 and the rebuilt 5173 frontend are now
active.

The Gateway listens on all interfaces at port 8000. The local Ollama boundary
is ready with both required models. A due scheduled source automatically began
the first production 0.18.0 scan, and its durable entry inventory and progress
events are increasing.

Rollback evidence is the custom-format database backup under
`backups/releases/0.18.0-20260730T0814Z`. Restore requires stopping the managed
Gateway, restoring into a separate PostgreSQL database, validating counts and
then changing the configured database URL. The source backup is retained
without changing the active database.
