# ADR 0021: Stable product knowledge and atomic generations

## Status

Accepted for 0.20.0.

## Context

The Project registry updates `product_version_id` when the configured product
version changes. Existing product-scoped chunks kept their earlier
ProductVersion. Exact ProductVersion filtering made those completed vectors
inaccessible even though both versions represented the same Product.

Processor upgrades also need to reconsider unchanged bytes without deleting the
last usable index before the replacement succeeds.

## Decision

Product-scoped retrieval resolves the current Project Product physical ID and
accepts chunks and code symbols from every ProductVersion belonging to that
Product. Tenant scope continues to use the Tenant physical ID.

Content hash determines byte changes. Processor fingerprint determines whether
the selected route, parser, chunker, embedding model and dimensions remain
compatible. Matching values reuse vectors. A changed processor fingerprint
reprocesses the file.

Each knowledge document stores `generation_ingestion_id`. Embeddings are
prepared before the database replacement transaction. Changed documents,
chunks, code facts, source fingerprint and ingestion completion commit
together. A source with completed documents remains searchable while a new
ingestion runs. Failure preserves the previous documents and approval state.

The source API reports actual accessible chunk counts and the most recent
completed ingestion as the active generation.

## Consequences

Existing product knowledge becomes available after deployment without vector
rebuild. Relearning can upgrade legacy files into newly supported processing
branches. Operational UI can distinguish searchable, refreshing, degraded,
empty and scope-mismatch states.

## Rollback

Downgrade Alembic to `20260730_0015` on PostgreSQL and revert the 0.20.0
release commit. Existing chunks remain unchanged because the generation field
is audit metadata.
