# ADR 0032: Content-addressed evidence and governed experience network

## Status

Proposed. Implementation is planned after the version 0.28.5 baseline.

## Context

CAG currently stores source observations, raw hashes, cleaned Document hashes,
encrypted Chunks, vectors, citations, code relationships and post-task
MemoryCandidates. Source locations can disappear or lose authorization. Cleaned
content has no independent immutable object copy. Approved MemoryCandidates are
not retrieved into later Codex tasks. Existing graph facts cover code but do
not provide one typed relation model across evidence, experience and Task
outcomes.

The production database already contains 113,908 Source Entries, 22,552
Documents, 183,091 Chunks and 623,429 embedding cache rows. This scale supports
bounded PostgreSQL and pgvector retrieval today. The expected relationship
network requires an explicit graph benchmark before the permanent graph engine
is selected.

## Proposed decision

1. Keep PostgreSQL as the system of record for physical identities, foreign
   keys, authorization, versions, governance, Tasks and audit.
2. Keep pgvector as the semantic candidate engine.
3. Add an S3-compatible, content-addressed Artifact Object Store for allowed
   raw snapshots, required cleaned objects, OCR results and transformation
   manifests.
4. Treat source paths and repository locations as mutable observations. They
   cannot be the sole representation of an accepted knowledge object.
5. Evaluate RustFS through the S3 abstraction. Retain an independent second
   copy for critical evidence until the selected deployment passes durability,
   recovery and upgrade acceptance.
6. Add typed, contextual relations across Evidence, Experience and Task nodes.
   Semantic similarity, factual support, contradiction, applicability,
   supersession and observed outcomes remain separate dimensions.
7. Retrieve approved Experience only after authorization, scope, status,
   validity and evidence-availability gates.
8. Persist a Task usage receipt and revalidate Experience from independent
   evidence, execution results and user corrections.
9. Implement graph access behind one projection interface. Benchmark relational
   adjacency tables, Apache AGE and an independent graph database at one
   million, five million and twenty million nodes before the final selection.
10. An independent graph database remains a rebuildable projection. PostgreSQL
    Outbox events and Artifact objects provide the rebuild source.
11. Rebuild existing knowledge in a new atomic Generation. Preserve the current
    Active Generation until object, provenance, retrieval and rollback gates
    pass.
12. Replace extension-only routing with MIME, magic, text-likelihood and
    sandboxed extractor selection. Never execute knowledge input.

## Consequences

Knowledge remains usable and verifiable after a source path disappears.
Experience can shorten later Codex work while retaining evidence, scope and
expiry. PostgreSQL, object storage and an optional graph projection have clear
recovery boundaries.

Storage and operational cost increase because important content has durable
copies and graph projections. Extraction has a larger attack surface and needs
process isolation, resource limits and a maintained format corpus. Graph and
object technologies cannot be declared production-ready without the acceptance
defined in the roadmap.

## Acceptance

The proposal becomes Accepted only when the implemented phase has all relevant
tests, migration or rebuild evidence, production-scale performance, object
recovery, authorization isolation, provenance closure, rollback and Browser
management evidence. A partial phase does not imply completion of later phases.

## Rollback

Keep the prior Active Knowledge Generation and PostgreSQL truth. Disable
Experience injection, stop graph projection consumers and restore object reads
to the previously verified replica. Projection data can be discarded and
rebuilt from committed PostgreSQL Outbox rows and content-addressed Artifacts.

## Detailed plan

See `docs/cag-evidence-experience-evolution-roadmap.md`.
