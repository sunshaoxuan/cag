# CAG 0.29.0 knowledge conversion baseline

## Objective

Implement roadmap Phase 0 as an operational capability: canonical lifecycle
states, a format capability matrix, a persisted Conversion Manifest schema and
a production-scale read-only dry run.

## Findings

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| Legacy `observed` was ambiguous | Production Source Entries and active Ingestion linkage used the same persisted status for discovered and active processing observations | high | Phase 0 projects canonical status and does not rewrite legacy rows |
| The largest Source is ready for an explicit conversion plan | Production dry run created 115,668 items in about 24 seconds | high | Content bytes were not inspected in Phase 0 |
| Existing knowledge was preserved | Source Entry, Document, Chunk, embedding cache, symbol, relation and MemoryCandidate counts were equal before and after dry run | high | Object backfill and reclean are later phases |
| The manifest has closed strong references | Production audit found zero missing Source Entry foreign keys and zero missing referenced Document foreign keys | high | Full Artifact links do not exist yet |
| A large reclean program is required | Production action count contains 99,933 reclean items | high | Extension metadata planning may change after Phase 2 MIME and magic inspection |
| Formal runtime serves the new contract | Supervised 0.29.0 runtime returned ready PostgreSQL and pgvector, format matrix, manifest detail and filtered items | high | UI does not yet expose the new APIs |

## Production result

Run `77ef2f49-8da2-437b-9ecf-a283a43bb326`:

```text
item_count=115668
manifest_sha256=80a9403250acefeb18a92449b61edf4f79718a46e6e653e15fb487f19df21ed4
lifecycle discovered=70156 indexed=462 metadata_only=44877 rejected=159 removed=14
action backfill_object=448 metadata_only=13362 path_only=954 reclean=99933 safe_unpack=971
```

Capability distribution:

```text
supported_text=70007
planned_text=22804
planned_ocr=1960
content_probe_required=5796
safe_unpack_candidate=971
binary_metadata=12606
sensitive_metadata=570
path_knowledge=954
```

## Boundary

Phase 0 writes planning records only. It does not copy raw or cleaned objects,
inspect MIME or magic, rebuild knowledge, create general graph relations or
inject approved Experience into Codex.
