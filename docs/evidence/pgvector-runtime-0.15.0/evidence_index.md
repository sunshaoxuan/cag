# Evidence index

| Evidence | Result |
|---|---|
| `backend/app/database.py` | Managed SQLite rejection and pgvector readiness |
| `backend/app/knowledge/service.py` | PostgreSQL native cosine ordering |
| `backend/app/migrations/sqlite_to_pgvector.py` | Controlled complete migration |
| `backend/alembic/versions/20260729_0013_pgvector_runtime.py` | Extension and HNSW index |
| `scripts/run-local-codex-gateway.ps1` | PostgreSQL startup gate |
| `scripts/migrate-sqlite-to-pgvector.ps1` | Operator migration entry point |
| `backend/tests/test_pgvector_integration.py` | Native vector and migration integration |
| `docs/evidence/screenshots/pgvector-runtime-0.15.0.jpg` | Browser management-page evidence |
| `docs/adr/0016-postgresql-pgvector-runtime-cutover.md` | Runtime and cutover decision |
| `live-migration-blocked/migration_report.json` | Actual active-job migration block |
