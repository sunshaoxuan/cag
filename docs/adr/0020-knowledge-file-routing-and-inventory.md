# ADR 0020: Knowledge file routing and durable inventory

## Status

Accepted in version 0.18.0.

## Context

A knowledge source can contain text documents, source code, empty files,
archives, database dumps, backups, binaries and files too large for safe
content extraction. The source path and file presence may remain operationally
useful even when content analysis is inappropriate.

Content hashes alone cannot detect an upgraded extractor, parser or routing
policy. Reusing a prior hash without processor identity can permanently retain
an old processing decision.

## Decision

Every observed entry has an independent `KnowledgeSourceEntry` UUID. It stores
the source-relative path, entry type, extension, 64-bit size, modification
time, presence, processing mode, status, reason and processor receipt.

The deterministic routing modes are:

* `metadata_only` for archives, dumps, backups, binaries and policy-sized files;
* `path_only` for zero-byte files;
* `code` for recognized source code;
* `document` for supported non-code content.

Metadata-only content is not opened, chunked or embedded. Path-only files create
semantic evidence from the registered relative path. Code always uses the
structural code analyzer. Documents use the standard extraction and chunking
pipeline.

Successful indexed documents store a processor fingerprint containing policy
version, processing mode, processor version, embedding model and dimensions.
Reuse requires both a matching content hash and compatible processor
fingerprint. Legacy non-code documents may receive the current fingerprint
without re-embedding. Legacy code documents are reprocessed once to populate
structural facts under the hard routing policy.

## Consequences

Operators can inspect the complete source inventory independently from the
searchable document set. Very large file sizes do not overflow database audit
fields. Tool upgrades can deliberately reprocess unchanged bytes. Matching
documents continue to reuse vectors.

This decision does not introduce independently leased per-file work items or
pause and resume controls. ADR 0015 retains those remaining requirements.

## Verification

Automated tests cover sparse files above 2 GiB, ZIP and dump metadata-only
routing, zero-byte path knowledge, code structural facts, inventory API
filters, legacy code reprocessing and unchanged document vector reuse.

## Rollback

Keep the new inventory table and restore the prior classification policy. The
processor policy version must change so affected files are reconsidered on the
next ingestion. The migration downgrade removes the new columns and table only
after dependent operational data is no longer required.
