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

This receipt covers the source release and isolated validation. The live
long-running learning process remains on its current version. After that run
reaches a terminal state, the planned restart applies migration
`20260730_0015`. A subsequent ingestion can reuse unchanged normal documents,
reprocess legacy code, and inventory metadata-only assets under the new policy.
