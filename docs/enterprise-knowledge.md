# Governed enterprise knowledge

## Boundary

The enterprise knowledge plane belongs to One Agent Gateway. Ollama supplies local model inference and Codex supplies the ChatGPT-authenticated engineering Agent. Frontends call CAG APIs and SSE only.

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
code symbols, relationships and documentation evidence
  |
Ollama embedding
  |
pgvector and keyword projection
  |
tenant and product authorization filter
  |
vector, Japanese keyword, symbol and graph recall
  |
reciprocal rank fusion
  |
optional local evidence reranking
  |
context budget and injection isolation
  |
Codex task with durable citations
  |
local memory candidate extraction
```

The managed source registry accepts local directories, authenticated Windows
UNC shares, Git repositories, GitLab repositories and SVN repositories. A
GitLab project wiki can be registered through its wiki Git URL. Each remote
source is materialized as a managed revision snapshot before extraction.

Supported input includes source code, scripts, configuration, Markdown, common
text formats, CSV, PDF, DOCX, PPTX, XLSX and ODT. Build outputs, dependencies
and repository metadata are excluded.

Version 0.18.0 records every discovered entry in a durable source asset
inventory. ZIP, DUMP, backup, binary and files above the default ten-megabyte
policy limit keep file presence, relative path, 64-bit size and processing
reason without content extraction or content vectors. Empty files create
path-only knowledge from the file name and relative path. Source code enters
the structural code analyzer. Supported non-code files enter the document
extractor.

Each successful document stores a processor fingerprint. The fingerprint
includes the routing policy, processing mode, processor version, embedding
model and vector dimensions. A changed fingerprint gives an unchanged file a
new processing opportunity. A matching content hash and fingerprint reuses the
existing chunks and vectors.

The managed knowledge store is PostgreSQL 16 with pgvector. Embeddings use the
native `vector(1024)` type and an HNSW cosine index. The vector channel executes
distance ordering inside PostgreSQL. SQLite is accepted only by isolated tests
and the one-time migration reader.

The ingestion stream reports collection, cleaning, indexing and Source Memory
persistence as separate durable stages. The Knowledge page follows this SSE
directly. Memory candidate governance has its own `/memory` page.

Every collection outcome outside the accepted document set is auditable.
Rejected and skipped entries are stored with source-relative path, stable
reason code, file metadata, extractor identity and sanitized exception detail.
The database supports paged operational queries and CSV export. Each run also
produces a gzip JSONL snapshot with a SHA 256 receipt. Database rows and
compressed archives use separate retention windows so the searchable working
set can rotate while longer-lived evidence remains available.

## Code knowledge plane

Code is indexed as text evidence and as structured facts. `CodeSymbol` stores
modules, classes, interfaces, structs, enums, functions and methods with the
canonical source path and line range. `CodeRelation` stores parser-observed
imports and calls. A resolved relation references the target symbol physical
ID. External and ambiguous targets remain explicit unresolved facts with a
confidence value.

`CodeDocumentLink` connects symbols to non-code documents only when a
deterministic path or symbol-name mention exists. The evidence record states the
matching method. Model-generated guesses are excluded from this fact table.
Changed documents replace their dependent symbols through database cascade.
The Gateway then rebuilds source relations and documentation links from stored
parser facts. Unique fingerprints prevent duplicate relations and links.

Python uses the standard library AST. The Linux Gateway image prefetches
Tree-sitter grammars for the supported code languages during image build. If a
native parser is unavailable, the language-aware fallback extracts definitions,
imports and calls and records the selected parser and diagnostics. This keeps
the ingestion auditable across Windows application-control policies and Linux
containers.

Text decoding recognizes UTF-8 BOM, UTF-8, UTF-16 BOM, CP932 and Shift-JIS.
Detected encoding is stored in chunk metadata. This covers Japanese Windows
repositories without silently replacing undecodable bytes.

## Durable synchronization

Knowledge locations remain in a persistent source registry. Each source chooses
`manual` or `scheduled` synchronization and stores its interval, next due time,
last attempt, last content change, failure count and current lease. The
Gateway scheduler claims one due source through a database row lock and an
expiring lease. This permits safe recovery after process restarts and prevents
duplicate work when more than one Gateway Worker polls the same database.

Every scheduled run scans the current source snapshot. The idempotent comparison
then separates unchanged, changed, added and removed paths. Only changed and
added files, plus files with changed processor fingerprints, require new
embeddings. Unchanged chunks retain their physical IDs and vectors. Removed
paths delete their documents and dependent chunks while their source inventory
entry remains marked absent. Each
run remains available as ingestion history with its trigger, status, counts,
timestamps, error and rejection archive receipt. The management page exposes
the file-level audit, CSV export and compressed archive from this history.

Failed scheduled runs increment the source failure counter and receive an
exponential retry delay bounded by the configured regular interval. A
successful run resets the failure counter and schedules the next interval.
Queued or running records found during Gateway startup become failed recovery
records, after which their sources can retry safely.

## Idempotent vector index

Every cleaned file is identified by source physical ID, canonical relative path and SHA 256 content hash. A source fingerprint is derived from the sorted path and hash set. Repeating ingestion with the same fingerprint writes no document, chunk or vector. Unchanged files keep their physical document and chunk IDs and reuse their stored vectors. Changed files replace only their own chunks. Removed files delete their indexed documents. Database uniqueness on source plus path and document plus ordinal prevents duplicate results.

The registry also computes a normalized source key from source type, location,
reference, subpath and scope. One Project cannot register the same logical
source twice. During a collection run, files with identical cleaned content
share a content hash and only the first canonical path is indexed. The
ingestion receipt reports unchanged files, reused vectors and duplicate files
separately.

## Source credentials

Source passwords and access tokens are written to the operating system
credential store under an opaque source credential reference. Database rows
contain the reference and optional username. API responses, SSE events and
logs never return the secret.

Git HTTP credentials are supplied to the child process through an environment
only authorization header. SVN secrets use `--password-from-stdin` together
with `--no-auth-cache`. Windows network share credentials use the native WNet
API and are disconnected after collection. Connector processes use argument
arrays without a command shell and pass the Command Policy allowlist.

## Managed source lifecycle

```text
register
  |
validate connection
  |
collect immutable Git or SVN revision, or read the selected directory
  |
extract and normalize supported files
  |
secret and Prompt Injection scan
  |
content deduplication and incremental comparison
  |
embedding and encrypted Source Memory persistence
  |
approved retrieval
```

Disabling a source prevents new collection and clears its schedule and lease.
Deleting a source removes its documents, chunks, ingestion history, credential
entry and managed snapshots.
Changing reference, subpath or scope invalidates the existing index so the next
run rebuilds it under the new governance boundary.

## Scope rules

Tenant chunks match only the current Project Tenant physical ID. Product chunks match the current ProductVersion physical ID. A source becomes retrievable only after local indexing and explicit Codex approval.

Task memories begin as encrypted tenant scoped candidates. Approval makes the record accepted for governance. Product promotion removes the tenant reference only after approval.

## Conversation knowledge loop

Every Conversation turn defaults to governed knowledge assistance. The Gateway
finishes retrieval before starting or resuming the Codex app-server turn.
Selected evidence is supplied through developer instructions with the encrypted
chunk plaintext opened only for the bounded runtime context. Each block carries
the source name, source type, canonical path, revision and `resource_uri`.

The same citation objects are written to `KnowledgeUsage`, emitted by
`knowledge.context.injected`, attached to the Task final report and stored in
MemoryCandidate evidence. This gives the answer, the learned memory candidate
and the original source one traceable chain. Source authorization, prompt
injection exclusion and context-size limits are applied before any evidence
reaches Codex.

## Models

`qwen3-embedding:8b` produces 1024 dimensional vectors. Query embeddings use an
instruction that asks for Japanese enterprise code and technical evidence while
preserving exact identifiers and paths. Retrieval applies Reciprocal Rank
Fusion to vector, Japanese keyword and code symbol channels. Related symbols
and documentation links expand the evidence set. The `deep` search profile uses
`qwen3:14b` for JSON Schema constrained candidate scoring. The model must return
every bounded candidate UUID exactly once. A complete response contributes one
additional RRF channel. Missing, duplicated or unknown IDs discard the entire
model channel, so semantic or structural evidence order cannot be overwritten
by a partial response. The same model extracts memory candidates. One Ollama
request executes at a time on the current 16GB GPU.

## Evidence and evaluation

Every injected chunk creates a KnowledgeUsage record with Task, rank and score.
Source identity, commit, canonical path and resource URI remain in the
citation. DataQualityMetric records accepted file ratio. Later Harness releases
add answer groundedness and conflict evaluation.
