# Evidence index

| Evidence | Purpose |
|---|---|
| `backend/app/knowledge/connectors.py` | Breadth-first directory queue and progress callback |
| `backend/app/knowledge/service.py` | Durable progress events and queued-state execution gate |
| `backend/app/api/knowledge.py` | Active-ingestion SSE reuse |
| `backend/app/knowledge/scheduler.py` | Start only newly created scheduled ingestion |
| `backend/tests/test_knowledge.py` | Queue order, progress counts and single-flight tests |
| `frontend/src/App.tsx` | Automatic scheduled-run following and readable progress |
| `frontend/src/App.test.tsx` | Progress SSE projection and visible-row control |
| `docs/adr/0012-breadth-first-source-collection.md` | Architecture decision and rollback |
| `docs/evidence/screenshots/directory-progress-0.12.0.jpg` | Live browser acceptance |
| `test_results.md` | Automated and live validation |
| `FINAL_RECEIPT.md` | Release acceptance and rollback receipt |
