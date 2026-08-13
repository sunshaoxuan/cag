# CAG evidence and experience roadmap investigation

## Question

Define a systematic next-stage CAG plan covering existing knowledge reuse or
rebuild, broader safe text extraction, durable evidence objects, an evidence
and experience relationship network, graph-engine selection and Codex feedback.

## Findings

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| The production knowledge database is already material | Live PostgreSQL reported about 11 GB, 113,908 Source Entries, 22,552 Documents, 183,091 Chunks and 623,429 embedding-cache rows | high | Point-in-time 2026-08-13 snapshot |
| Current ingestion coverage is incomplete | The main production Source had 69,367 observed, 43,910 metadata-only, 460 indexed and 132 rejected entries during the snapshot | high | One scheduled Ingestion was active, so observed is not a terminal failure classification |
| Extension-only routing excludes useful text | `backend/app/knowledge/extractors.py` supports a fixed set of modern Office, PDF, text and code extensions; production audit contains legacy Office, mail, RTF, images, scripts and configuration types as unsupported | high | Individual files still require MIME and content inspection |
| Cleaned evidence lacks an independent object layer | Cleaned Chunk content is encrypted in PostgreSQL; the inspected model has no content-addressed Artifact object reference | high | Existing rejection gzip archives are audit snapshots, not complete cleaned evidence objects |
| Current scale can begin with bounded PostgreSQL relations | Persisted general relationships are much smaller than Chunk and vector data, and current retrieval already uses bounded PostgreSQL and pgvector queries | medium | Million-edge and ten-million-edge traversal benchmarks have not run |
| RustFS is a candidate that needs an explicit maturity gate | Official documentation describes S3 compatibility, Apache 2.0, consistency and erasure coding; the official repository currently presents a beta release and distributed-mode work in progress | high | Product status must be refreshed before implementation |

## Decision

Adopt the seven-stage roadmap in
`docs/cag-evidence-experience-evolution-roadmap.md`. Start with production
baseline and Conversion Manifest work. Preserve PostgreSQL as the system of
record, introduce an S3-compatible content-addressed object abstraction, add a
typed relation projection interface and select the graph engine only through
reproducible scale benchmarks.

## Execution boundary

This task changed planning and requirements documentation only. It did not
change schemas, extraction behavior, production data, object storage, graph
storage or runtime services.
