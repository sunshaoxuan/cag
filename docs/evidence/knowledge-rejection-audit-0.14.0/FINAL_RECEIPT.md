# Version 0.14.0 release receipt

## Delivered

* One Agent Gateway product naming and visible `v0.14.0` header marker.
* Durable per-entry rejection and skip records with physical UUIDs and
  ingestion foreign keys.
* Relative path, disposition, extension, size, reason, extractor, exception
  type, sanitized message and timestamp.
* Paged JSON query, filtering, UTF-8 BOM CSV export and gzip JSONL download.
* Archive SHA 256 receipt and independent database and archive retention.
* Knowledge source overview, search, filter, create, edit, enable, disable,
  validate, trigger, history and learning run center.
* ADR 0015 for resumable, parallel and path-complete ingestion.

## Verification

Backend tests, coverage, migration checks, frontend tests, TypeScript build,
browser interaction, console inspection and screenshots passed. See
`test_results.md`.

## Deployment boundary

The verified source is ready for version control. The existing 0.12.0 ingestion
continues on the Windows managed runtime. Production process replacement and
database migration are intentionally deferred until that run reaches a safe
terminal state.

## Rollback

Downgrade Alembic to `20260728_0011`, revert the 0.14.0 release commit and
retain compressed audit archives until the configured evidence obligation is
satisfied.
