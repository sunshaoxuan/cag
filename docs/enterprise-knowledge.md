# Governed enterprise knowledge

## Boundary

The enterprise knowledge plane belongs to Agent Gateway. Ollama supplies local model inference and Codex supplies the ChatGPT-authenticated engineering Agent. Frontends call CAG APIs and SSE only.

## Modular RAG

```text
Source registration
  |
classification and immutable version
  |
secret scan and normalization
  |
structure-aware chunks
  |
Ollama embedding
  |
pgvector and keyword projection
  |
tenant and product authorization filter
  |
vector and keyword recall
  |
reciprocal rank fusion
  |
context budget and injection isolation
  |
Codex task with durable citations
  |
local memory candidate extraction
```

The initial implementation supports code, Markdown and common text source files. Build outputs, dependencies, binaries, Git metadata and files over two megabytes are excluded.

## Idempotent vector index

Every cleaned file is identified by source physical ID, canonical relative path and SHA 256 content hash. A source fingerprint is derived from the sorted path and hash set. Repeating ingestion with the same fingerprint writes no document, chunk or vector. Unchanged files keep their physical document and chunk IDs and reuse their stored vectors. Changed files replace only their own chunks. Removed files delete their indexed documents. Database uniqueness on source plus path and document plus ordinal prevents duplicate results.

## Scope rules

Tenant chunks match only the current Project Tenant physical ID. Product chunks match the current ProductVersion physical ID. A source becomes retrievable only after local indexing and explicit Codex approval.

Task memories begin as encrypted tenant scoped candidates. Approval makes the record accepted for governance. Product promotion removes the tenant reference only after approval.

## Models

`qwen3-embedding:8b` produces 1024 dimensional vectors. `qwen3:14b` produces JSON Schema constrained memory candidates and remains the quality reranker adapter target. One Ollama request executes at a time on the current 16GB GPU.

## Evidence and evaluation

Every injected chunk creates a KnowledgeUsage record with Task, rank and score. Source commit and canonical path remain in the citation. DataQualityMetric records accepted file ratio. Later Harness releases add answer groundedness and conflict evaluation.
