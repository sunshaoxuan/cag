# Evidence index

| Claim | Evidence |
|---|---|
| Stable Product scope | `backend/app/knowledge/service.py` |
| Version sync committed before independent knowledge session | `backend/app/api/knowledge.py` |
| Generation audit field and backfill | `backend/alembic/versions/20260730_0016_stable_product_knowledge.py` |
| Failed refresh preserves old knowledge | `backend/tests/test_knowledge.py` |
| Real source retrieval health | `backend/app/api/knowledge.py`, `frontend/src/App.tsx` |
| Architecture decision | `docs/adr/0021-stable-product-knowledge-generations.md` |
| Browser acceptance | `docs/evidence/screenshots/stable-product-knowledge-0.20.0.png` |
