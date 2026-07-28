# Evidence index

| Claim | Evidence |
|---|---|
| Japanese Windows text is accepted | `backend/tests/test_code_intelligence.py` |
| Code symbols and calls are extracted | `backend/app/knowledge/code_intelligence.py`, backend tests |
| Structural records use UUID and foreign keys | `backend/app/models/knowledge.py`, migration 0011 |
| Reingestion is idempotent | `backend/tests/test_knowledge.py` |
| Search includes symbol and graph evidence | `backend/app/knowledge/service.py`, API test |
| Code knowledge has an independent route | `frontend/src/App.tsx`, frontend route test |
| Linux image has cached grammars | Gateway image build and Java parser smoke |
| Governance and rollback are documented | ADR 0013 and task learning receipt |
