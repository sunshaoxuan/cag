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

The managed source registry accepts local directories, authenticated Windows
UNC shares, Git repositories, GitLab repositories and SVN repositories. A
GitLab project wiki can be registered through its wiki Git URL. Each remote
source is materialized as a managed revision snapshot before extraction.

Supported input includes source code, scripts, configuration, Markdown, common
text formats, CSV, PDF, DOCX, PPTX, XLSX and ODT. Build outputs, dependencies,
binary executables and repository metadata are excluded. The default size limit
is ten megabytes per file and can be reduced by deployment policy.

The ingestion stream reports collection, cleaning, indexing and Source Memory
persistence as separate durable stages. The Knowledge page follows this SSE
directly. Memory candidate governance has its own `/memory` page.

## Durable synchronization

Knowledge locations remain in a persistent source registry. Each source chooses
`manual` or `scheduled` synchronization and stores its interval, next due time,
last attempt, last content change, failure count and current lease. The
Gateway scheduler claims one due source through a database row lock and an
expiring lease. This permits safe recovery after process restarts and prevents
duplicate work when more than one Gateway Worker polls the same database.

Every scheduled run scans the current source snapshot. The idempotent comparison
then separates unchanged, changed, added and removed paths. Only changed and
added files require new embeddings. Unchanged chunks retain their physical IDs
and vectors. Removed paths delete their documents and dependent chunks. Each
run remains available as ingestion history with its trigger, status, counts,
timestamps and error.

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

## Models

`qwen3-embedding:8b` produces 1024 dimensional vectors. `qwen3:14b` produces JSON Schema constrained memory candidates and remains the quality reranker adapter target. One Ollama request executes at a time on the current 16GB GPU.

## Evidence and evaluation

Every injected chunk creates a KnowledgeUsage record with Task, rank and score. Source commit and canonical path remain in the citation. DataQualityMetric records accepted file ratio. Later Harness releases add answer groundedness and conflict evaluation.
