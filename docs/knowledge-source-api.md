# Managed knowledge source API

## Source types

| `source_type` | `location` | Optional fields |
|---|---|---|
| `local_directory` | Authorized absolute host directory | `subpath` |
| `network_share` | Windows UNC path such as `\\server\share\docs` | credential, `subpath` |
| `git` | Git URL or authorized local repository | credential, `reference`, `subpath` |
| `gitlab` | GitLab project or wiki Git URL | credential, `reference`, `subpath` |
| `svn` | SVN URL | credential, `reference`, `subpath` |

`credential_secret` is accepted on create or update. Source list and maintenance
responses never return it. `credential_configured` indicates whether an
operating system credential reference exists.

## Register

```http
POST /api/v1/knowledge/sources
Content-Type: application/json
```

```json
{
  "project_id": "cag",
  "name": "Product documentation",
  "source_type": "gitlab",
  "location": "https://gitlab.example.com/team/product.git",
  "reference": "main",
  "subpath": "docs",
  "scope": "product",
  "approved_for_codex": true,
  "sync_mode": "scheduled",
  "sync_interval_minutes": 60,
  "credential_username": "oauth2",
  "credential_secret": "<write-only token>"
}
```

The legacy `root_path` create field remains accepted for
`local_directory`. New callers use `location`.

## Maintain and validate

```text
GET    /api/v1/knowledge/sources
PATCH  /api/v1/knowledge/sources/{source_id}
DELETE /api/v1/knowledge/sources/{source_id}
POST   /api/v1/knowledge/sources/{source_id}/validate
```

Patch supports `name`, `source_type`, `location`, `reference`, `subpath`,
`scope`, `enabled`, `approved_for_codex`, credential rotation and
`clear_credential`. It also supports `sync_mode` with `manual` or `scheduled`
and `sync_interval_minutes` from 1 through 10080. Updating any location
identity field invalidates the prior index and managed snapshot. Send an empty
`reference` or `subpath` to clear it.

The source response includes `next_sync_at`, `last_sync_attempt_at`,
`last_content_change_at`, `consecutive_failures` and `scheduler_claimed`.
These fields allow API clients and the management page to monitor persistent
source health without reconstructing state from transient logs.

It also includes `entry_summary` with total, present, absent, processing-mode
and status counts from the durable source inventory.

## Reveal a saved credential

```http
POST /api/v1/knowledge/sources/{source_id}/credential/reveal
```

```json
{
  "username": "oauth2",
  "secret": "<saved password or token>"
}
```

The action reads the operating system credential store only after an explicit
request. Responses carry `Cache-Control: no-store, private`, `Pragma: no-cache`
and `X-Content-Type-Options: nosniff`. Source list, ingestion history, SSE and
task audit responses continue to exclude the secret.

The web management page calls this action when editing a source whose
`credential_configured` field is true. The loaded value starts masked and can
be displayed or copied. Production exposure requires caller authentication and
project authorization.

## Collect and follow

```text
POST /api/v1/knowledge/sources/{source_id}/ingest
GET  /api/v1/knowledge/sources/{source_id}/ingestions
GET  /api/v1/knowledge/ingestions/{ingestion_id}
GET  /api/v1/knowledge/ingestions/{ingestion_id}/events
```

The event endpoint is SSE. It supports `after_sequence` and `follow`, matching
the resumable CAG event convention.

存在確認用 Session は Streaming Response の返却前に閉じる。Event Polling は反復ごとに
独立した短命 Session を使用し、Transaction を閉じてから Event を送信する。
Rejection CSV Export は500件単位の Keyset Pagination を使用し、各 Batch の Session を
閉じてから CSV Row を送信する。長時間接続及び低速 Client は Database Transaction を
保持しない。
管理 Frontend は企業知識画面を表示している間だけ実行中 Ingestion の SSE を接続し、
別画面へ遷移した時点で接続を閉じる。

Durable stage events:

```text
knowledge.ingestion.queued
knowledge.ingestion.started
knowledge.collection.started
knowledge.collection.progress
knowledge.collection.completed
knowledge.cleaning.started
knowledge.cleaning.completed
knowledge.indexing.started
knowledge.indexing.completed
knowledge.rejection.archive.created
knowledge.rejection.archive.failed
knowledge.memory.persisted
knowledge.ingestion.completed
knowledge.ingestion.failed
```

Folder-backed sources emit `knowledge.collection.progress` at the start and
completion of every directory. The event data contains:

```json
{
  "phase": "completed",
  "directory": "docs/product",
  "directories_scanned": 4,
  "directories_pending": 7,
  "files_discovered": 120,
  "files_processed": 100,
  "current_directory_files": 24,
  "rejected_files": 1,
  "skipped_files": 3
}
```

`directory` is relative to the registered source root. The collector lists one
directory, closes its operating system directory handle, processes that
directory's supported files and then advances to the next queued directory.
Directories use breadth-first order, so the first level becomes visible before
deep descendants. Excluded dependency and version-control directories are not
queued.

An encrypted or unreadable PDF increments `rejected_files` and collection
continues. Credentials discovered in adjacent files are never used to decrypt
documents automatically. Unsupported extensions and files over the configured
size limit increment `skipped_files`.

If the ingest action is called while the same source already has a queued or
running ingestion, the API returns that active ingestion and attaches the
caller to its SSE. It does not schedule another execution.

The management page retains at most the latest 200 progress events in browser
memory and counts the complete received stream separately. Selecting 50, 100 or
200 changes only the rendered projection. The backend event ledger remains
complete and resumable.

The terminal ingestion record includes `files_seen`, `chunks_written`,
`rejected_files`, `skipped_files`, `duplicate_files`, `unchanged_files`,
`vectors_reused`, `changed_files`, `removed_files`, `trigger`, `started_at`,
`completed_at` and compressed rejection archive metadata. The source ingestion
list retains the latest fifty runs.

## File processing audit

Every discovered filesystem entry is upserted into `KnowledgeSourceEntry`.
This inventory remains available independently from a successful document or a
rejection record.

```text
GET /api/v1/knowledge/sources/{source_id}/entries
```

The endpoint supports `limit`, `offset`, `processing_mode`, `present` and
`query`. Each item includes relative path, entry kind, extension, 64-bit file
size, modified time, processing mode, status, reason, current presence,
fingerprints, `extractor`, `extractor_version` and first, last, processed or
removed timestamps.

Processing modes are:

| Mode | Behavior |
|---|---|
| `metadata_only` | Record path and filesystem metadata without content extraction |
| `path_only` | Create path knowledge for a zero-byte file |
| `document` | Use the supported document extraction and text chunking flow |
| `code` | Use structural code parsing, symbols and relationship analysis |

ZIP, DUMP, backup, binary and files over the configured size limit use
`metadata_only`. A processor-policy change updates the fingerprint so unchanged
bytes can be reconsidered on a later ingestion.

XLSX document entries use the `openpyxl` extractor and
`xlsx_semantic_v1` processor variant. The extracted text contains ordered sheet
headers and populated cell coordinates. Formulas retain their expression and
include the last cached value when the workbook supplies one. The extractor
does not calculate formulas. Workbooks exceeding the populated-cell or output
budget are rejected with `spreadsheet_cell_limit_exceeded` or
`spreadsheet_text_limit_exceeded`. Office lock files beginning with `~$` are
skipped with `temporary_office_file`.

Repeated rejection callbacks for one ingestion and path update one audit row.
Rejected outcomes take precedence over skipped outcomes and counters describe
unique final paths.

## Conversion baseline dry run

```text
GET  /api/v1/knowledge/conversion/format-capabilities
POST /api/v1/knowledge/sources/{source_id}/conversion-baselines
GET  /api/v1/knowledge/conversion-baselines/{run_id}
GET  /api/v1/knowledge/conversion-baselines/{run_id}/items
```

The POST action freezes a planning snapshot from persisted Source Entries,
current-path Documents and the newest queued or running Ingestion. It writes a
separate Conversion Manifest and never changes the source inventory, Documents,
Chunks, embeddings or active knowledge generation.

The baseline maps legacy inventory observations to `discovered`, `processing`,
`indexed`, `metadata_only`, `rejected` or `removed`. Every item proposes one
conversion action and retains the complete input snapshot. The item endpoint
supports pagination and filters by lifecycle status or conversion action.
Stable ordering and canonical JSON hashing make an unchanged dry run produce
the same `manifest_sha256`.
PostgreSQL reads and writes a successful Manifest in one `REPEATABLE READ`
transaction. Any failure rolls back all item batches and closes the independent
run record with a sanitized terminal error.

The format capability endpoint is an explicit Phase 0 planning matrix. It
separates current text support, planned text, planned OCR, safe-unpack
candidates, executable binary metadata and sensitive metadata. It does not
claim that file bytes have passed MIME, magic or text-likelihood detection.

The source list response includes:

* `active_generation_id`, the most recent completed ingestion.
* `retrieval_health.status`, one of `searchable`, `refreshing`, `degraded`,
  `indexing`, `scope_mismatch`, `approval_required`, `disabled` or `empty`.
* `retrieval_health.total_chunks` and `accessible_chunks`.
* `retrieval_health.legacy_documents`, which identifies documents eligible for
  a processor upgrade.

Product scope uses the stable Product physical ID. All ProductVersion records
for that Product share completed knowledge. Tenant scope continues to require
an exact Tenant physical ID.

Every rejected or skipped source entry creates one
`KnowledgeIngestionRejection` row with an independent UUID physical ID and an
ingestion foreign key. The row stores the source-relative path, entry kind,
disposition, extension, size, stable reason code, extractor, exception type,
sanitized error message and timestamp.

```text
GET /api/v1/knowledge/ingestions/{ingestion_id}/rejections
GET /api/v1/knowledge/ingestions/{ingestion_id}/rejections/export
GET /api/v1/knowledge/ingestions/{ingestion_id}/rejections/archive
```

The JSON endpoint supports `limit`, `offset`, `disposition`, `reason_code` and
`extension`. It returns the filtered total and an unfiltered reason summary.
The export endpoint returns UTF-8 BOM CSV. The archive endpoint returns the
immutable gzip JSONL snapshot created for the run. Its first line is a header
with schema version, ingestion ID, source ID, record count and creation time.

Stable reason codes include `unsupported_extension`, `file_too_large`,
`encoding_unsupported`, `empty_text`, `directory_read_error`,
`file_stat_error`, `file_permission_denied`, `file_read_error`,
`pdf_unreadable`, `office_archive_invalid`, `extractor_unavailable` and
`extractor_rejected`.

Database detail and compressed archives have separate retention settings.
Default retention is 90 days for queryable rows and 365 days for gzip files.
Pruning applies only after a terminal run has a completed archive. Relative
paths and sanitized errors avoid placing the registered absolute source root
in audit output.

## Scheduled lifecycle

```text
registered source
  |
next_sync_at becomes due
  |
database lease claim
  |
breadth-first directory queue
  |
per-directory progress events
  |
incremental hash comparison
  |
reuse, replace, add and remove
  |
persist run receipt
  |
schedule next interval or bounded retry
```

New API clients may choose either sync mode explicitly. The web management form
defaults to scheduled synchronization. Sources created before version 0.10.0
are migrated as manual so a deployment upgrade does not unexpectedly contact
external systems.

## Idempotency

The normalized source key prevents duplicate registration inside a Project.
Cleaned content hashes remove duplicate files inside one source snapshot.
Canonical path plus content hash reuses unchanged documents and vectors across
repeated runs. The sorted path and hash set produces the final source
fingerprint.

## Structural code indexing

Supported code files run through structural analysis after cleaning. The
ingestion stream emits:

* `knowledge.code.analysis.completed` with changed code-file, symbol and parser
  counts.
* `knowledge.code.graph.persisted` with current source symbol, relationship and
  documentation-link counts.

The source fingerprint, content hash and processor fingerprint are the
idempotency authority. Unchanged files with the same processor fingerprint
retain their vectors and symbols. A changed processor fingerprint reprocesses
the file even when its bytes are unchanged.
Changed and removed files replace dependent structural records. Relationship
and documentation evidence is rebuilt with unique fingerprints before the
ingestion completes.

Code knowledge can be queried through `/api/v1/knowledge/code/*`. These
endpoints expose only approved sources that match the requested Project Tenant
or stable Product.

## Content-addressed evidence objects

Version 0.30.0 introduces the object evidence foundation. Cleaned evidence,
allowed raw snapshots, OCR pages, structured tables and manifests use a SHA 256
object key. PostgreSQL stores the physical Artifact identity, mutable source
observation, replica address, version, ETag, checksum and integrity status.

```text
PUT  /api/v1/knowledge/artifacts
GET  /api/v1/knowledge/artifacts/summary
GET  /api/v1/knowledge/artifacts/{sha256}
GET  /api/v1/knowledge/artifacts/{sha256}/content
POST /api/v1/knowledge/artifacts/reconciliation-runs
```

An Artifact becomes queryable after two independent replicas pass checksum
verification and the database transaction commits. Repeated content reuses one
Artifact physical ID. A missing replica can be restored from the remaining
healthy replica. When every replica is unavailable, content reads return
`artifact_unavailable` while the current active knowledge generation continues
to serve indexed retrieval.

`replicated-filesystem` is the production default for the initial durability
gate. `s3` configures the primary store through an S3-compatible endpoint such
as RustFS and retains the independent filesystem replica. The application never
uses a RustFS-specific API.

## Universal safe extraction

Version 0.31.0 routes files from detected content. The persisted evidence
contains MIME, magic type and text probability. Untrusted parsers run in a
network disabled child process with a hard timeout and limits for input,
output, archive members, expanded bytes and compression ratio. Archive paths,
links and traversal attempts are rejected before member content is used.

The registry covers plain text with unknown extensions, RTF, EML, MSG, legacy
OLE Office containers, XLS, safe ZIP text members, OOXML, PDF and image OCR.
Every rejection records processor, processor version, stable reason code and
retryability. Cleaned complete text is persisted as a SHA 256 Artifact linked
to the Source Entry, so it remains readable after its observed path disappears.

Artifact write, metadata, content and reconciliation endpoints require the
operations administrator headers. The aggregate summary contains counts only
and remains available to the knowledge management page.

Artifact encryption uses the independent `artifact-evidence` key in Windows
Credential Manager. Artifact metadata stores a non-secret truncated key ID so
operators can identify the required key during recovery. This key is separate
from the enterprise knowledge Chunk key and cannot change the decryptability of
existing indexed knowledge.
