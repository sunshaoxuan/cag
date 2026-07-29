# Evidence index

| Evidence | Purpose |
|---|---|
| `backend/app/tasks/executor.py` | Proves retrieval precedes runtime execution and citations enter the final report and memory capture |
| `backend/app/knowledge/service.py` | Proves bounded context construction, resource metadata and grounding evidence |
| `backend/app/knowledge/resources.py` | Proves source-specific resource URI generation |
| `backend/app/runtimes/codex_app_server.py` | Proves developer instructions enter `thread/start` and `thread/resume` |
| `backend/tests/test_knowledge.py` | Covers Conversation retrieval, SSE citation, final report and MemoryCandidate evidence |
| `backend/tests/test_codex_app_server_runtime.py` | Covers resource-linked context delivery to the app-server protocol |
| `docs/adr/0017-conversation-knowledge-grounding-loop.md` | Records the accepted contract and rollback |
| `docs/evidence/screenshots/conversation-knowledge-loop-0.16.0.png` | Browser evidence for the 0.16.0 Conversation console |
