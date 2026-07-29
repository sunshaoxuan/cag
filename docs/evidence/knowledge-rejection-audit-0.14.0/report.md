# One Agent Gateway 0.14.0 evidence report

## Scope

Version 0.14.0 adds durable file-level rejection audit, compressed retention,
knowledge source lifecycle management, the learning run center, the One Agent
Gateway product name and the visible release version.

## File audit evidence

The synthetic enterprise source contained:

* one accepted Markdown document;
* one byte sequence rejected as `encoding_unsupported`;
* one empty SQL file rejected as `empty_text`;
* one legacy DOC file skipped as `unsupported_extension`;
* one text file skipped as `file_too_large`.

The completed ingestion persisted four rejection or skip rows. The JSON API
returned relative paths, dispositions, stable reason codes, file metadata and
sanitized exception evidence. UTF-8 BOM CSV and gzip JSONL downloads contained
the same records. The archive header reported schema version, ingestion ID,
source ID and record count.

The retention test aged the archive receipt past 90 days and verified that
queryable rows were pruned while the gzip file remained. It then aged the file
past 365 days and verified archive removal.

## Management UI evidence

The production frontend bundle was served on an isolated validation port and
connected to a temporary 0.14.0 backend database. The browser confirmed:

* `One Agent Gateway v0.14.0` in the persistent header;
* source count, enabled count, running count and attention count;
* source search, status filter and create action;
* edit, history, validation, learning, enable or disable and delete actions;
* continuously visible learning run center;
* ingestion history counts for rejected and skipped files;
* Chinese reason summaries and exact relative paths;
* CSV export and gzip archive links.

Browser console output was empty. Screenshots:

* `docs/evidence/screenshots/knowledge-source-management-0.14.0.jpg`
* `docs/evidence/screenshots/knowledge-rejection-audit-0.14.0.jpg`

## Current-runtime boundary

Read-only inspection found that the currently running 0.12.0 Windows managed
process uses `workspaces/.gateway/agent_gateway.db` and has no PostgreSQL
connection. Its vectors are stored through the SQLite JSON compatibility type.
The running ingestion was not stopped or restarted.

ADR 0015 records PostgreSQL plus pgvector migration, durable file work items,
parallel leases, pause and resume, per-file atomic commits and path-complete
semantic indexing as planned work. This report does not claim those capabilities
are implemented in 0.14.0.
