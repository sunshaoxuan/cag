# Evidence index

| Evidence | Path |
|---|---|
| Source model and idempotent fields | `backend/app/models/knowledge.py` |
| Source connector boundary | `backend/app/knowledge/connectors.py` |
| Credential store | `backend/app/knowledge/credentials.py` |
| Document extraction | `backend/app/knowledge/extractors.py` |
| Collection and index orchestration | `backend/app/knowledge/service.py` |
| Source API and SSE | `backend/app/api/knowledge.py` |
| Database migration | `backend/alembic/versions/20260728_0009_knowledge_sources.py` |
| Backend acceptance tests | `backend/tests/test_knowledge.py` |
| Migration round trip | `backend/tests/test_migrations.py` |
| Frontend component acceptance | `frontend/src/App.test.tsx` |
| Source management UI | `frontend/src/App.tsx` |
| API contract | `docs/knowledge-source-api.md` |
| Design decision | `docs/adr/0007-managed-knowledge-sources.md` |
| Source page screenshot | `docs/evidence/screenshots/managed-knowledge-sources-0.9.0.png` |
| Ingestion stage screenshot | `docs/evidence/screenshots/managed-knowledge-ingestion-0.9.0.png` |
| Source edit screenshot | `docs/evidence/screenshots/managed-knowledge-source-edit-0.9.0.jpg` |
