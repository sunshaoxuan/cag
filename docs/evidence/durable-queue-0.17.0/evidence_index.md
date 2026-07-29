# Version 0.17.0 evidence index

| Evidence | Purpose |
|---|---|
| `backend/app/queue/service.py` | PostgreSQL admission, claim, lease and recovery |
| `backend/app/queue/coordinator.py` | Interactive and knowledge worker pools |
| `backend/app/queue/notifier.py` | Redis wake notifications and polling fallback |
| `backend/alembic/versions/20260729_0014_durable_work_queue.py` | Physical queue and migration receipt schema |
| `backend/app/migrations/auto_cutover.py` | Guarded and idempotent restart cutover |
| `frontend/src/ApiDocsPage.tsx` | Online API reference and call examples |
| `docs/adr/0018-postgresql-redis-durable-queue.md` | Architecture decision |
| `backend/tests/test_queue.py` | Queue behavior and recovery tests |
| `backend/tests/test_auto_cutover.py` | Cutover gate and receipt tests |
| `backend/tests/test_pgvector_integration.py` | Real PostgreSQL vector and migration validation |
| `docs/evidence/screenshots/durable-queue-api-docs-0.17.0.png` | Browser evidence for the online API reference |
| `test_results.md` | Executed verification results |
| `FINAL_RECEIPT.md` | Release and rollback receipt |
