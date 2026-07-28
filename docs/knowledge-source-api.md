# Managed knowledge source API

## Source types

| `source_type` | `location` | Optional fields |
|---|---|---|
| `local_directory` | Authorized absolute host directory | `subpath` |
| `network_share` | Windows UNC path such as `\\server\share\docs` | credential, `subpath` |
| `git` | Git URL or authorized local repository | credential, `reference`, `subpath` |
| `gitlab` | GitLab project or wiki Git URL | credential, `reference`, `subpath` |
| `svn` | SVN URL | credential, `reference`, `subpath` |

`credential_secret` is accepted only on create or update and is never returned.
`credential_configured` indicates whether an operating system credential
reference exists.

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

## Collect and follow

```text
POST /api/v1/knowledge/sources/{source_id}/ingest
GET  /api/v1/knowledge/sources/{source_id}/ingestions
GET  /api/v1/knowledge/ingestions/{ingestion_id}
GET  /api/v1/knowledge/ingestions/{ingestion_id}/events
```

The event endpoint is SSE. It supports `after_sequence` and `follow`, matching
the resumable CAG event convention.

Durable stage events:

```text
knowledge.ingestion.queued
knowledge.ingestion.started
knowledge.collection.started
knowledge.collection.completed
knowledge.cleaning.started
knowledge.cleaning.completed
knowledge.indexing.started
knowledge.indexing.completed
knowledge.memory.persisted
knowledge.ingestion.completed
knowledge.ingestion.failed
```

The terminal ingestion record includes `files_seen`, `chunks_written`,
`rejected_files`, `duplicate_files`, `unchanged_files`, `vectors_reused`,
`changed_files`, `removed_files`, `trigger`, `started_at` and `completed_at`.
The source ingestion list retains the latest fifty runs.

## Scheduled lifecycle

```text
registered source
  |
next_sync_at becomes due
  |
database lease claim
  |
complete source snapshot
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
