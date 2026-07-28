# Version 0.13.0 release receipt

## Delivered

* Japanese enterprise text decoding metadata.
* Native and fallback code parsers.
* Symbol-boundary chunks.
* Code symbol, relation and documentation-link records.
* Idempotent source graph rebuild.
* Japanese, vector, symbol and graph hybrid search.
* Optional local deep reranking.
* Scoped code knowledge APIs and SSE facts.
* Independent Code Knowledge management route.
* Architecture, API, security, deployment, ADR and control documentation.

## Current verification

Automated backend, frontend, migration, Compose, image and Linux native parser
verification passed. A scheduler-disabled 0.13.0 Gateway performed a real
Ollama ingestion and deep search against the host knowledge database. The
browser rendered four symbols, three relationships, four documentation links,
one resolved call and linked Markdown evidence. Console output was empty and
both overview and detail screenshots were saved.

The main 8000 process remains on the prior runtime until its pre-existing
network-share ingestion finishes. This release verification did not interrupt
or duplicate that scan.

## Rollback

Downgrade Alembic to `20260728_0010`, revert the 0.13.0 release commit and
redeploy 0.12.0. Existing semantic documents, chunks and vectors remain.
