# Final receipt

CAG 0.30.0 implements Phase 1 of the evidence and experience roadmap. It adds
content-addressed Artifact, ArtifactLocation, ObjectReplica,
ArtifactTransformation and reconciliation records. Object bytes use an
independent AES GCM key and two verified replicas on separate volumes.

The formal production database is at migration 0029 and the supervised runtime
is ready on version 0.30.0. A controlled Artifact remained readable after the
primary object was removed, and reconciliation restored the primary from the
second replica. Database and object orphan counts are zero. Existing knowledge
table counts remained unchanged.

RustFS is supported through an S3-compatible adapter and protocol tests. The
formal primary remains filesystem-backed until RustFS completes the roadmap
distributed recovery and endurance gate.

The inherited enterprise knowledge encryption key is unavailable. This release
does not replace that key and preserves all old ciphertext and provenance.
Recovery requires the original key or a governed new-Generation rebuild from
accessible sources. That incident remains visible in the formal UI and API.
