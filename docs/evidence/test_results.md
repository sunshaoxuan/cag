# Current release test results

Date: 2026-08-05

Version: 0.22.8

## Automated

| Check | Result |
|---|---|
| Backend Pytest | 129 passed, 2 environment-dependent tests skipped |
| Backend coverage | 86.06 percent, required minimum 85 percent |
| Frontend Vitest | 17 passed in 3 files |
| Frontend TypeScript and production build | Passed |
| Alembic 0020 upgrade and downgrade | Passed |
| Real target workbook read-only parse | 14 sheets, 1001 populated cells, 47 formulas, 47 cached values |

The backend suite was rerun from the beginning after each version assertion
correction. The final complete run passed.

## Isolated runtime

The candidate backend ran on 127.0.0.1:8001 with an isolated SQLite database
and Fake Runtime. The candidate frontend ran on 127.0.0.1:5174 and proxied the
isolated backend. Version 0.22.8 loaded successfully.

The Knowledge page opened a source-scoped file inventory, submitted a relative
path query, cleared the query and rendered the processor and processed-time
columns. Desktop and 720-pixel viewport checks passed. Browser warning and
error console entries were zero. Temporary processes, database, logs and
workspace files were removed after validation.

Screenshots:

* `docs/evidence/xlsx-ingestion-reliability-0.22.8/knowledge-inventory-desktop.png`
* `docs/evidence/xlsx-ingestion-reliability-0.22.8/knowledge-inventory-narrow.png`

## Production acceptance

Production cutover and the complete UPDS learning run are recorded in the
version-specific final receipt after deployment.
