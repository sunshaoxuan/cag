# Safe extraction framework investigation

## Outcome

CAG 0.31.0 replaces extension-only routing with content probing and a bounded
extractor registry. It preserves the existing high-quality OOXML, XLSX, PDF and
PDF OCR extractors, and adds isolated handling for unknown-extension text, RTF,
EML, MSG, OLE, legacy XLS and safe ZIP members. Common images enter OCR.

## Findings

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| Unknown extension text enters cleaning | `test_unknown_extension_text_is_detected_and_extracted` | high | Corpus fixture |
| Binary input is never executed | Registry has no executable handler and binary corpus returns `binary_content_not_extractable` | high | Operating system containment remains process-level |
| Archive attacks are rejected | Traversal, expanded-size, member and compression ratio checks plus corpus tests | high | ZIP is the implemented archive format in this phase |
| Every extraction failure is stable and auditable | Migration 0030 and API archive/CSV fields | high | Historical failures retain their old recorded fields |
| Cleaned content survives source-path loss | Cleaned Artifact, two replicas and ArtifactLocation Source Entry link | high | New links are created by 0.31.0 ingestion |

The enterprise knowledge key was unavailable before this phase and remains
unavailable. Existing ciphertext, vectors, documents, chunks and provenance are
preserved. Phase 2 does not claim that historical ciphertext has become
decryptable.
