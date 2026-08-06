# ADR 0026: Multilingual customer knowledge learning

## Status

Accepted for version 0.24.0.

## Context

Customer identity and operational meaning can exist in directory names, file
names, document text or scanned images. Version 0.23.0 embedded document text
without its canonical path, skipped embeddings in customer fast search, and
limited customer extraction to contracts, services, VPNs and environments.
Files discovered after the last successful source generation remained visible
in inventory while unavailable to retrieval. Image only PDFs produced
`empty_text`. Japanese credential labels were not redacted.

The production UPDS source demonstrated all of these conditions in the
`し_0276_滋賀大学/V6/６．リモート接続情報` directory.

## Decision

1. Keep Qwen3 Embedding as the multilingual semantic model. Embed a structured
   representation containing canonical path and redacted chunk text.
2. Keep bounded lexical and exact path recall. Fuse lexical, vector and exact
   channels with reciprocal rank fusion. Customer extraction uses semantic
   retrieval for business sections.
3. Resolve customer roots from the governed source inventory. Retrieval no
   longer requires a customer file to have an existing chunk before its root
   can be identified.
4. Preserve every physical file path. Content deduplication may reuse content
   work but may not discard a path.
5. Convert unreadable, unsupported and metadata only file paths into explicit
   path evidence. Path evidence proves asset existence and never proves file
   content.
6. OCR image only PDF pages with Tesseract using Japanese and English language
   data. Store page markers, extractor version and OCR processing metadata.
7. Redact multilingual credentials and protected connection values before
   encryption input, search projection, embedding, structured extraction and
   model context.
8. Add `remote_access` and `repositories` customer sections. A protocol or
   repository candidate requires authoritative content evidence. Path evidence
   can create a learning gap or asset notice only.
9. Report source freshness independently from governance approval. Consecutive
   failures and an incomplete active generation make retrieval health degraded.
10. Keep scheduled learning incremental. Unchanged file metadata and current
    processor fingerprints reuse the existing physical document and vectors.
11. Deduplicate parser facts by the persisted code symbol identity before
    database insertion. A repeated parser fact cannot roll back an otherwise
    valid long running ingestion.
12. Checkpoint embeddings after each successful batch using only the model,
    dimensions, redacted input hash and vector. A retry calculates missing
    batches while searchable knowledge changes only after complete ingestion.
13. PostgreSQL lexical candidates use at most eight indexable terms. Two
    character CJK fragments remain semantic signals and cannot force a global
    substring scan.
14. A governed Source subpath is part of the semantic embedding path. Stored
    canonical paths stay relative to that Source so resource URIs remain
    stable and do not duplicate the subpath.
15. Store separate raw-file, cleaned-document and knowledge-chunk SHA 256
    values. KnowledgeDocument strongly references SourceEntry by physical ID;
    every Citation exposes that entry ID and can resolve back to the governed
    file URI.
16. Backfill legacy raw-file hashes independently with bounded concurrent file
    reads and batch commits. The raw hash itself is the checkpoint. A rerun
    selects only missing hashes. If stored size or modification time differs
    from the physical file, leave the hash missing and require normal ingestion
    to rebuild the cleaned document and chunks.

## Established patterns

Qwen documents Qwen3 Embedding as multilingual and cross lingual across more
than 100 languages:
https://qwenlm.github.io/blog/qwen3-embedding/

pgvector documents hybrid search and recommends reciprocal rank fusion or a
cross encoder for combining full text and vector results:
https://github.com/pgvector/pgvector#hybrid-search

Tesseract documents searchable PDF output and explicit language selection:
https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html

OCRmyPDF documents OCR text layers for scanned PDFs and sidecar text output:
https://ocrmypdf.readthedocs.io/en/stable/

## Consequences

The release changes embedding fingerprints and requires reindexing governed
documents. Existing physical IDs remain stable only for unchanged documents
whose current fingerprint is reusable. OCR adds Tesseract and PDF rendering as
runtime dependencies. Missing OCR dependencies are explicit readiness and
rejection evidence.

Remote connection summaries contain protocol, purpose, freshness and citations.
Credentials remain outside searchable knowledge. Repository claims require
explicit repository evidence. Cross language queries use semantic recall while
codes, paths, protocol names and abbreviations retain exact lexical recall.
Legacy provenance backfill can resume after process or host interruption and
does not invoke OCR, cleaning, embedding or a generative model.

## Acceptance

1. A Chinese query retrieves Japanese SSH evidence whose customer identity
   exists only in the path.
2. An image only Japanese PDF creates OCR text with page evidence.
3. Japanese password values are absent from ciphertext plaintext input,
   `search_text`, embeddings, model prompts, API results and logs.
4. Two paths with identical content remain independently retrievable.
5. Customer extraction returns typed SSH and LDAP remote access candidates and
   no SVN candidate without SVN evidence.
6. A source with repeated failed refreshes reports degraded freshness even when
   it remains approved for governance.
7. A second unchanged ingestion reuses documents and vectors without repeated
   OCR or embedding.
8. Duplicate parser facts produce one persisted symbol and the ingestion
   completes without a uniqueness error.
9. A forced embedding failure resumes from persisted checkpoints and does not
   repeat completed model work.
10. Closure audit reports zero orphan documents, orphan chunks, missing chunk
    hashes and missing embeddings. Every readable file has a raw byte hash.
11. A clean PostgreSQL database upgrades from the first Alembic revision to
    0024, and SQLite to pgvector cutover preserves physical provenance IDs.

## Rollback

Restore version 0.23.0, restore the pre release PostgreSQL backup and remove the
0.24.0 OCR runtime dependencies. Do not retain mixed 0.23.0 and 0.24.0
processor fingerprints.
