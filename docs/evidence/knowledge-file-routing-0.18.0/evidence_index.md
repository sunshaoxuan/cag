# Evidence index

| Evidence | Result |
|---|---|
| `backend/app/knowledge/processing_policy.py` | Deterministic metadata, path, document and code routing |
| `backend/app/models/knowledge.py` | Durable source entry inventory and 64-bit file sizes |
| `backend/alembic/versions/20260730_0015_source_entry_routing.py` | PostgreSQL schema migration |
| `backend/tests/test_knowledge.py` | Large sparse file, ZIP, dump, path-only, hard code routing and fingerprint reuse |
| `backend/tests/test_migrations.py` | Migration and column type assertions |
| `frontend/src/App.test.tsx` | File asset summary, table and compact error behavior |
| `docs/evidence/screenshots/knowledge-file-inventory-detail-0.18.0.png` | Isolated browser rendering |
| `test_results.md` | Automated and live-isolated validation results |
