# Governed enterprise knowledge

## Boundary

The enterprise knowledge plane belongs to One Agent Gateway. Ollama supplies local model inference and Codex supplies the locally authenticated engineering Agent. The local Codex session may use ChatGPT or a Codex API Key. Frontends call CAG APIs and SSE only.

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
pgvector, pg_trgm and keyword projection
  |
tenant and product authorization filter
  |
bounded exact text, vector Top K, symbol and graph recall
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

XLSX files use openpyxl in read-only mode with external workbook links
disabled. The semantic representation preserves workbook sheet order, sheet
name and visibility, populated cell coordinates, normalized values, formulas
and cached formula values when present. Dates use ISO text and embedded line
breaks are escaped. Charts, macros and style-only information remain outside
the spreadsheet knowledge text. Hidden sheets remain eligible for indexing.
PDF pages whose text layer is empty use Tesseract OCR with Japanese and English
language data. OCR output preserves page markers and extractor version evidence.

One workbook is limited to 250000 populated cells by default. Extracted text
also remains inside the configured file-size character budget. A limit breach
creates a stable rejection reason. Office lock files whose names begin with
`~$` remain visible in the source inventory and are skipped as temporary files.

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

The XLSX processor adds `xlsx_semantic_v1` to its fingerprint. Existing
non-XLSX document fingerprints retain their previous payload, so the parser
upgrade reprocesses spreadsheets while unchanged ordinary documents continue
to reuse stored vectors.

Product-scoped knowledge follows the stable Product physical ID. ProductVersion
records remain release and provenance metadata. A Project version change keeps
all completed knowledge from the same Product eligible for retrieval.

Every indexed document records the ingestion physical ID that produced its
current representation. Embeddings are prepared before the replacement
transaction. Changed documents, chunks, code symbols, graph facts, source
fingerprint and ingestion status commit together. Readers continue to see the
previous committed representation until that transaction succeeds. A failed
refresh preserves the previous searchable generation and records a degraded
health state.

The managed knowledge store is PostgreSQL 16 with pgvector and pg_trgm.
Embeddings use the native `vector(1024)` type and an HNSW cosine index. Each
embedding input contains the canonical path and redacted chunk text so customer
and operational meaning carried by directories remains available to semantic
retrieval. Lowered
Chunk text, document paths and symbol names use GIN trigram indexes. Every
channel has a fixed candidate limit. The `fast` profile performs no model call,
while `balanced` and `deep` add bounded vector and reranking stages. SQLite is
accepted only by isolated tests and the one-time migration reader.

The API and durable queue worker run in separate operating-system processes.
Knowledge saturation therefore does not occupy the API event loop. Retrieval
events expose stage, profile, elapsed time, candidate counts, Source IDs and
active Generation IDs. Customer ledger extraction uses a dedicated
`extraction` queue and Worker pool, resolves one Catalog Scope from the Source
and organization attributes,
builds an exhaustive file manifest and validates typed candidates against
authoritative Chunk and Document Version citations.

The ingestion stream reports collection, cleaning, indexing and Source Memory
persistence as separate durable stages. The Knowledge page follows this SSE
directly. Memory candidate governance has its own `/memory` page.

Every collection outcome outside the accepted document set is auditable.
Rejected and skipped entries are stored with source-relative path, stable
reason code, file metadata, extractor identity and sanitized exception detail.
Persistence merges repeated paths inside and across buffer flushes. A rejected
outcome has priority over a skipped outcome and ingestion counters represent
unique final paths.
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
embeddings. Unchanged chunks retain their physical IDs and vectors. Changed and
absent paths move their previous documents and chunks into immutable history
while the source inventory records current presence. Archive chunks stay
outside normal retrieval and remain available for version and audit queries. Each
run remains available as ingestion history with its trigger, status, counts,
timestamps, error and rejection archive receipt. The management page exposes
the file-level audit, CSV export and compressed archive from this history.

Failed scheduled runs increment the source failure counter and receive an
exponential retry delay bounded by the configured regular interval. A
successful run resets the failure counter and schedules the next interval.
Sources with a completed generation remain approved and searchable during a
refresh and after a refresh failure.
Queued or running records found during Gateway startup become failed recovery
records, after which their sources can retry safely.

## Idempotent vector index

Every physical file has a streamed raw byte SHA 256 on its SourceEntry. Cleaned documents and knowledge chunks have separate content hashes because each proves a different transformation boundary. KnowledgeDocument stores a required physical foreign key to SourceEntry, and KnowledgeChunk stores a required foreign key to KnowledgeDocument. A source fingerprint is derived from the sorted path and cleaned hash set. Repeating ingestion with unchanged size, modification time, raw hash and processor fingerprint writes no document, chunk or vector. Unchanged files keep their physical document and chunk IDs and reuse their stored vectors. Changed files create a new Document and Document Version, activate a new Processing Version after quality completion, mark the prior Processing Version superseded and archive prior chunks. Removed files follow the same historical retention rule. Knowledge Block Versions keep immutable values and evidence. Applicability Revisions keep business effective periods independently from Processing Versions. Embeddings of redacted path and content input are checkpointed by model, dimensions and input hash after every successful batch. A failed refresh resumes from these checkpoints and retains the previous Active Processing Version until the replacement transaction completes.

Legacy sources backfill original-byte provenance with:

```powershell
.\.venv\Scripts\python.exe -m app.knowledge.provenance_backfill <source-id>
```

The command selects only present file entries whose raw hash is missing, reads
files with bounded concurrency, and commits each batch. The stored raw hash is
the restart checkpoint. A file whose size or modification time differs from
the inventory remains unhashed so normal ingestion can atomically refresh its
cleaned document and chunks. This command never runs OCR, embeddings or a
generative model.

The registry also computes a normalized source key from source type, location,
reference, subpath and scope. One Project cannot register the same logical
source twice. During a collection run, files with identical cleaned content
share a content hash and every canonical path is indexed. The
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

Tenant chunks match only the current Project Tenant physical ID. Product chunks
match every ProductVersion that belongs to the current Project Product physical
ID. Gateway and frontend release changes therefore retain completed enterprise
knowledge. A source becomes retrievable after local indexing and explicit
Codex approval.

The source API reports `retrieval_health` with total and accessible chunk
counts, legacy-document count, health state and active generation ID. The
management badge uses this result instead of treating the source workflow
status as proof of retrievability.

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
