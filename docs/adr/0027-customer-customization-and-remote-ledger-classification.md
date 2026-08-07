# ADR 0027: Customer customization and remote ledger classification

## Status

Accepted for version 0.25.0.

## Context

The governed customer source contains dedicated `２．カスタマイズ情報` and
`６．リモート接続情報` directories. Scoped Extraction maintained a second,
narrower extension list than Knowledge Ingestion. This caused ingested SQL
source material to appear as `unsupported_extension` in the exhaustive
manifest. OneOps also had no typed customization field or physical record.

## Decision

1. Scoped Extraction uses the same supported extension registry as Knowledge
   Ingestion. Source-entry processing state remains authoritative for metadata
   only, failed and observed-only material.
2. Add `CUSTOMER_CUSTOMIZATION_V1` with a small structured contract for name,
   category, summary, business purpose, affected components, status and notes.
3. Treat remote connection knowledge as VPN and Environment business records.
   Remove the obsolete independent Remote Access schema.
4. Process `.xlsm` with the existing bounded Spreadsheet extractor. Macro code
   is not executed.
5. Executables, databases, archives and other metadata-only assets may prove
   that a file exists. They cannot prove customization behavior or connection
   facts.
6. A queue Worker checks and requeues leases that expire after Worker startup
   within the next claim transaction. Long-running ingestion resumes from its
   persisted embedding checkpoint.
7. Active-ingestion reuse requires the same Source, Analysis Scope physical ID
   and Scope Prefix. An unscoped source refresh cannot satisfy a Scope Repair
   request.
8. Scope Repair starts collection at the selected Prefix and prefixes collected
   paths back to the Source-relative canonical form. Observation finalization
   can mark removed entries only inside that Prefix.
9. Metadata-only files are not opened for raw-byte hashing. Their governed
   evidence is limited to path, size, modification time and policy reason.
10. Embeddings remain in proven batches of 8. Duplicate cache keys inside a
    batch are generated and inserted once, while checkpoint commits remain
    durable between batches.
11. Connector collection uses the Scope Prefix as its starting subpath. The
    embedding semantic path uses only the original Source subpath because the
    collected canonical path already contains the Scope Prefix.
12. The current OneOps contract requests analysis Template version 2. Version
    1 remains immutable historical state and version 2 owns the expanded schema
    registry.
13. The customer extraction API accepts template version 2 as its only current
    request contract. Each model output field is constrained by a field-specific
    JSON Schema variant. Object-list values use the registered object schema in
    the generation format, including required snake-case properties and the
    prohibition on additional properties.
14. Named organizations used by production acceptance are samples only. Scope
    resolution remains driven by the request subject physical identity,
    business attributes, source physical identity and Catalog contents. No
    sample code, name or directory is a runtime default or branch condition.
15. Customer field extraction sanitizes decrypted active Chunk text again before
    constructing the model prompt and sanitizes Citation excerpts independently.
    Credential detection includes labeled connection fields, credential URLs
    and slash-separated account plus strong-password spreadsheet values.
16. Field routing uses the governed business directory taxonomy for every
    customer. Customization documents request only customization objects;
    remote-information documents request only VPN and Environment objects;
    other directories cannot generate these three special ledger fields. This
    keeps the model schema small and prevents unrelated document inference.
17. Different values of an object-list field represent independent business
    records and remain independently reviewable candidates. Same-priority
    different-value conflict detection continues to apply to scalar and master
    fields where only one current ledger value can be selected.
18. Ingestion execution claims a queued physical ingestion with a conditional
    database update before collection starts. A direct caller and the queue
    worker therefore cannot collect the same scope concurrently.

## Consequences

SQL customization sources participate in exhaustive analysis after normal
ingestion. OneOps can create strongly referenced customization, VPN and
Environment records from reviewed candidates. Unsupported binary assets remain
visible in coverage and require an independently supported extractor before
their content can become evidence.

## Acceptance

1. An ingested `.sql` Source Entry is `ready` in the Scoped Extraction manifest.
2. A valid customization object passes the registered schema and has content
   Citation evidence.
3. Remote information creates VPN and Environment candidates.
4. Credentials and protected connection values are absent from candidates,
   logs and evidence excerpts.
5. `.xlsm` content uses the bounded Spreadsheet extraction path.
6. A metadata-only oversized archive completes without reading its bytes.
7. A failed multi-batch embedding refresh reuses the committed first batch and
   completes on retry without duplicate cache-key inserts.
8. Real Qwen structured generation for a customization document and a VPN
   document produces values that pass the registered customization, VPN and
   Environment schemas without post-generation shape repair.
9. A slash-separated account and strong-password value is absent from the
   model prompt, candidate value and Citation excerpt. Ordinary file paths
   remain unchanged.
10. Directory routing is verified with organization-neutral paths and the
    separate `0276` integration fixture. Production modules contain no sample
    organization code or name.
11. Two distinct VPN objects from two documents produce two selected candidates
    with no scalar-value conflict. Scalar conflict coverage remains unchanged.
12. Concurrent execution attempts create one collection start event and invoke
    the scoped connector once.

## Rollback

Restore version 0.24.0 and its database backup. Reanalyze affected customer
Scopes after returning to the previous processing policy fingerprint.
