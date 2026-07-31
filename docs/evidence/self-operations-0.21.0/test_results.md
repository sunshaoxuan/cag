# Version 0.21.0 test results

| Gate | Result |
|---|---|
| Backend full suite | 113 passed, 2 skipped, coverage 85.73% |
| PostgreSQL native pgvector storage and search | passed |
| Completed SQLite to PostgreSQL pgvector migration | passed |
| Alembic target revision | `20260731_0017` |
| PowerShell supervisor suite | 9 passed |
| Frontend unit suite | 14 passed |
| Frontend production build | passed |
| Browser page content | passed |
| Browser console | 0 warnings, 0 errors |
| 1265px responsive header | 9 navigation items, all single line |
| Isolated issue workflow | `waiting_approval`, 2 artifacts, 9 events |

The first combined PostgreSQL command created the migration target without an
Alembic baseline. Its migration case failed before any transfer because
`data_migration_receipts` was absent. The target was upgraded to
`20260731_0017`, matching the production launcher sequence, and the same
migration case passed. This confirms the required startup ordering and records
the failed setup attempt rather than omitting it.
