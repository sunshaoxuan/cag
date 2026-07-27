# Evidence index

| Evidence | Purpose | Result |
|---|---|---|
| `backend/app/api/tasks.py` | External task admission and trace response | Implemented |
| `backend/app/api/audit.py` | Audit query and global SSE API | Implemented |
| `backend/app/services/task_service.py` | Idempotency and global sequence assignment | Implemented |
| `backend/app/events/sse.py` | Task, Conversation and Audit SSE formatting | Implemented |
| `backend/tests/test_external_api_audit.py` | Trace, replay, filters and resume | Passed |
| `frontend/src/App.tsx` | Test console and API monitor | Implemented |
| `docs/evidence/screenshots/external-api-audit-0.8.0.png` | Real external Trace in browser | Passed |
| Trace `5c7fe35f-5f5a-4d07-a6d1-ad2b99f2cbed` | Real subscription Codex external call | Completed |
