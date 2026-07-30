# ADR 0015: Resumable and path-complete knowledge ingestion

## Status

Partially accepted through version 0.18.0. PostgreSQL with pgvector, native
vector search, controlled SQLite migration, durable source-entry inventory,
processor fingerprints and zero-byte file path knowledge are implemented.
Per-file work items, independent path vectors for every entry, parallel leases,
pause and resume remain planned.

## Problem statement

The current collector builds the complete accepted source snapshot in memory,
computes all changed embeddings and commits documents, hashes, chunks, vectors,
code facts, source fingerprint and terminal state in one final database
transaction. Hashes and vectors are therefore synchronized at commit. A
process interruption before that commit discards the current run's computed
embeddings.

Rejected and skipped files do not receive a `KnowledgeDocument` hash and do
not enter the source fingerprint. They are retried on the next complete scan.
An extraction failure can currently cause a previously successful document at
the same path to be treated as removed.

Only extracted content becomes searchable knowledge. A zero-byte file, an
unsupported file and a directory can carry business meaning in their names and
relative paths, while the current semantic index excludes that information.

The managed Windows host runner used to default to a SQLite file. Version
0.15.0 makes PostgreSQL with pgvector mandatory before resumable parallel
workers are enabled.

## Decision

### Separate observation from successful indexing

Every encountered entry receives a durable `KnowledgeSourceEntry` physical
UUID. The record stores source ID, normalized relative path, entry kind,
extension, size, modified time, optional streaming byte hash and last observed
run.

Observation fields never decide that extraction can be skipped. A separate
successful processor receipt stores:

* extracted content hash;
* path semantic hash;
* extractor and parser versions;
* extraction policy fingerprint;
* embedding model and dimensions;
* indexed generation ID;
* successful completion time.

A prior failure is retried when the source is scanned again. It is also
requeued when the extractor version, parser version, policy fingerprint or
embedding model changes, even when the observed byte hash is unchanged.

### Treat paths as knowledge

Every directory and file creates path-semantic evidence from:

* complete source-relative path;
* each directory segment;
* file stem, suffix and entry kind;
* size and selected non-secret filesystem metadata;
* explicit indication that a file is empty, unsupported or unreadable.

Path evidence is indexed independently from content extraction. A zero-byte
file such as `本番環境では実行禁止.txt` remains useful evidence. Content
extraction failure does not remove its path evidence.

The raw absolute source root remains outside prompts, logs and vectors. Search
results cite the registered source and relative path.

### Durable work queue and leases

Each run creates `KnowledgeIngestionWorkItem` rows. PostgreSQL workers claim
items with a bounded lease and `FOR UPDATE SKIP LOCKED`. A work item moves
through:

```text
discovered
  |
observed
  |
path_index_pending
  |
extract_pending
  |
chunk_pending
  |
embed_pending
  |
commit_pending
  |
completed
```

Policy skips and extraction failures are terminal outcomes for the current
attempt. They remain eligible for later attempts. Lease expiry returns an
unfinished item to the queue without duplicating completed versions.

### Per-file atomic commit

Embeddings are staged with the document version. One database transaction then
writes the successful content receipt, chunks, vectors, code facts and path
evidence and switches the entry's active version. The transaction commits
before the work item becomes `completed`.

The old active version remains queryable until the new version commits. A
failed re-extraction preserves the old successful content and records the
new failure as a separate attempt. Source deletions are confirmed only after
the discovery phase completes.

This boundary keeps file hashes and vectors synchronized while allowing
parallel files to make durable progress.

### Pause, resume and cancellation

An ingestion accepts `pause_requested`, `resume_requested` and
`cancel_requested` control actions. Workers check control state between
bounded extraction, chunk and embedding batches.

Pause stops new claims and lets in-flight atomic units reach a checkpoint.
Resume reclaims remaining work. Cancellation preserves completed work,
attempt logs and queue state and closes the run as `cancelled`. A later run can
reuse completed processor receipts and requeue unfinished or failed entries.

### Full observability

Each state transition writes an ingestion event and an immutable work-attempt
record. The management UI shows:

* worker count and claimed work;
* discovered, queued, processing, completed, failed and skipped counts;
* current paths with bounded and sanitized error evidence;
* throughput and estimated remaining work;
* pause, resume and cancel state;
* compressed run and rejection archives.

Summary counts remain projections of work records. They are not the sole
evidence.

### Storage boundary

The managed runtime uses PostgreSQL 16 plus pgvector. SQLite remains available
only inside isolated automated tests and the one-time migration reader. The
Windows launcher rejects a SQLite runtime.

Migration from the current SQLite runtime requires a dry run, row and vector
counts, foreign-key validation, sampled vector comparison and an operator
receipt before switching the managed task.

## Acceptance criteria

* Interrupt after at least one committed file and prove restart does not
  recompute that file.
* Prove a file hash and all active vectors switch in one transaction.
* Prove an extraction failure retains the previous successful active version.
* Upgrade a fake extractor version and prove a previously failed unchanged file
  is requeued.
* Index and retrieve information carried only by a zero-byte filename and its
  directory path.
* Run at least two workers and prove each work item has one active lease.
* Pause during embedding, resume and complete without duplicate chunks.
* Compare SQLite migration source counts with PostgreSQL destination counts and
  pgvector dimensions before cutover.

## Version 0.18.0 implementation boundary

Completed acceptance evidence covers source-entry observation, metadata-only
archive and dump routing, 64-bit sizes, zero-byte filename knowledge, hard code
routing, legacy code fingerprint backfill and unchanged document vector reuse.

The current ingestion transaction still commits the run as one compatibility
unit. Durable per-file work items, independently committed active versions,
multi-worker file claims, pause and resume require a later release and their
remaining acceptance tests above.

## Rollback

Disable worker claiming, keep the prior active document versions and run the
single-worker compatibility path. PostgreSQL migration cutover retains the
SQLite source as a read-only backup until the acceptance receipt is approved.
