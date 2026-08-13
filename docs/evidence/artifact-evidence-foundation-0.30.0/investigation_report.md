# Investigation report

## Scope

CAG Phase 1 establishes durable content-addressed evidence objects without
changing the existing active knowledge generation. The investigation covered
the roadmap, ADR 0032, current production scale, RustFS official status, S3
integrity conventions, current runtime configuration and production recovery.

## Findings

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| Phase 1 now has a closed object evidence model | Artifact, ArtifactLocation, ObjectReplica, ArtifactTransformation and reconciliation tables with physical UUID and foreign keys | high | Historical knowledge conversion belongs to Phase 3 |
| Object identity is content-addressed | SHA 256 key validation, duplicate content reuse and encrypted object bytes | high | SHA 256 protects identity and integrity, not authorization by itself |
| A source path can disappear without losing selected evidence | Production primary-disconnect read succeeded from the C drive replica | high | The production sample is controlled and contains no customer data |
| Replica recovery is bidirectional | Unit tests restore either replica; production reconciliation restored the disconnected primary | high | Seven-day RustFS durability remains a separate gate |
| RustFS remains an S3 compatibility target | Official documentation presents S3 workloads, versioning and replication; the repository marks distributed mode under testing | high | Status was refreshed on 2026-08-13 and may change later |
| Existing knowledge content was not rewritten | Source Entry 115,693, Document 22,552, Chunk 183,091 and embedding cache 623,429 were unchanged across the production exercise | high | Existing Chunk decryption remains affected by the historical key loss |
| Historical enterprise knowledge key is unavailable | `/api/v1/knowledge/status` reports `knowledge encryption key is unavailable`; Credential Manager, environment and protected configuration audit found no recoverable key | high | Old ciphertext is retained and cannot currently be decrypted |
| Artifact encryption is isolated from the historical key | Independent Credential Manager entry, Key ID `f438b8e78e049c9d`, AES GCM ciphertext and separate loader | high | Credential Manager backup policy needs operational governance |

## Architecture decision

The formal runtime uses the standard `ArtifactObjectStore` boundary. The first
verified primary is on drive D and the independent replica is on drive C. The
S3 adapter is covered by an in-memory protocol contract and can target RustFS.
RustFS is not declared as the durable production primary until the roadmap
compatibility, distributed recovery and seven-day endurance gate passes.

Artifact bytes use an independent AES GCM key. PostgreSQL stores only the
truncated non-secret Key ID. Two verified replicas must exist before the
database publishes an Artifact. Ordinary content reads require administrator
authentication and an `available` database state.

## Inherited knowledge-key incident

The formal 0.29.0 runtime already reported the missing enterprise knowledge
key before the Phase 1 migration. A new knowledge key was not created because
that would make old ciphertext appear configured while remaining undecipherable.
All ciphertext, vectors, Source Entries, Documents and provenance records are
preserved. Recovery requires the original key or a new Generation rebuilt from
accessible Source Observations, followed by shadow retrieval and atomic
activation.
