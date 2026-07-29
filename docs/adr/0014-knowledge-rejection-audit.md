# ADR 0014: Durable knowledge rejection audit

## Status

Accepted for version 0.14.0.

## Context

Knowledge ingestion previously retained only aggregate rejected-file counts.
The collector continued after a file failure, while the relative path,
classification reason and extractor exception were discarded. Aggregate
metrics support progress display and quality ratios. They cannot support
incident review, remediation, reprocessing decisions or an enterprise audit.

Keeping all historical detail in the transactional database indefinitely
would increase the operational table size for large source trees. Keeping only
process log lines would weaken queryability, referential integrity and
retention control.

## Decision

Each rejected or skipped source entry is a durable
`KnowledgeIngestionRejection` business record with an independent UUID physical
ID and a foreign key to its ingestion. It records:

* source-relative path and entry kind;
* rejected or skipped disposition;
* extension and file size when available;
* stable reason code and extractor identity;
* exception type and sanitized bounded message;
* creation timestamp.

The ingestion service persists records in bounded batches during collection.
After collection, it creates one schema-versioned gzip JSONL archive, computes
SHA 256 and stores the archive receipt on the ingestion. A terminal failure
also attempts a partial archive before closing the run.

The operational API provides paged and filtered JSON, UTF-8 BOM CSV export and
compressed archive download. The management page exposes the same evidence
from ingestion history with Chinese reason labels.

Queryable rows default to 90-day retention. Compressed archives default to
365-day retention. Database rows are eligible for pruning only after a
terminal ingestion has a completed archive. Both windows are deployment
settings.

## Security

Paths are relative to the registered source root. Error messages replace the
absolute source root, remove line breaks and stop at 1000 characters. Archive
resolution is constrained to the configured directory. Export and download
responses prevent caching and content-type sniffing.

## Consequences

Operators can identify every skipped or failed file and distinguish policy
decisions from extraction failures. CSV supports remediation workflows. The
compressed snapshot supports longer evidence retention with lower storage
cost.

The running ingestion that predates this schema cannot reconstruct file paths
or reasons from its existing aggregate counters. Full file-level evidence
starts after deploying this version and running collection again.

## Rollback

Downgrade Alembic to `20260728_0011`, revert the 0.14.0 release commit and
remove retained `*.jsonl.gz` files only after the operator confirms their
retention obligations. Database downgrade removes rejection rows and archive
receipt columns.
