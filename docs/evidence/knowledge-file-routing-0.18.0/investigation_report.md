# Knowledge file routing investigation

## Scope

Version 0.18.0 addresses four operational gaps:

* large file sizes could overflow a 32-bit rejection field;
* ZIP, dump, backup and similar files lacked an explicit metadata-only policy;
* successful file hashes did not identify the processor policy or version;
* operators could not inspect a durable inventory of all discovered entries.

The running production learning task and the listeners on ports 8000 and 5173
were excluded from mutation and restart during implementation.

## Implemented flow

```text
filesystem observation
  |
durable KnowledgeSourceEntry
  |
deterministic processing policy
  | metadata_only: ZIP, dump, backup, binary, oversized
  | path_only: zero-byte file
  | document: supported non-code content
  | code: structural analyzer
  |
content hash plus processor fingerprint
  |
reuse matching vectors or reprocess changed policy
```

Metadata-only entries keep the relative path, type, extension, 64-bit size,
modification time, current presence and policy reason. Their content is not
opened, chunked or embedded.

Legacy code documents without a processor fingerprint are reprocessed once.
Legacy non-code documents with unchanged content receive the current document
fingerprint and keep their existing vectors. A later processor-policy change
changes the fingerprint and gives unchanged bytes another processing
opportunity.

## Remaining boundary

This release keeps the existing ingestion-level transaction and queue. Durable
per-file leases, independently committed active file versions, pause and resume
remain tracked by ADR 0015.
