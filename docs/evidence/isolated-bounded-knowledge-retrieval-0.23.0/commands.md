# Commands

| Purpose | Command summary | Result |
| --- | --- | --- |
| Backend complete suite | `backend\.venv\Scripts\python.exe -m pytest` | 134 passed, 3 skipped, coverage 85.25 percent |
| PostgreSQL boundaries | Explicit fresh PostgreSQL URLs for pgvector and process isolation tests | 3 passed |
| Migration | `python -m alembic upgrade head` | Production at `20260806_0021` |
| Migration round trip | Upgrade, downgrade and upgrade on PostgreSQL | passed during focused migration acceptance |
| Frontend | bundled `pnpm.cmd test -- --run` and `pnpm.cmd build` | 17 passed and production build succeeded |
| PowerShell | Parser for four scripts and Pester | parse passed and 10 passed |
| Compose | `docker compose config --quiet` | passed |
| Images | `docker compose build gateway worker frontend` | all images built |
| Backup | PostgreSQL custom format dump and `pg_restore -l` | readable 1,776,349,708 byte backup |
| Source quality | `git diff --check` | passed |

## Runtime probes

Production probes covered `/health/live`, `/health/ready`, Queue status, Task
status, cancellation, direct fast search, customer ledger extraction, Source
status, active Generation, PostgreSQL extensions and trigram indexes.
