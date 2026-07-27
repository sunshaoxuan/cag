# Evidence index

## Version 0.7.2

* `docs/evidence/PAGED_FRONTEND_FINAL_RECEIPT.md`
* `docs/evidence/screenshots/paged-overview-0.7.2.png`
* `docs/evidence/screenshots/paged-conversation-0.7.2.png`
* `docs/evidence/screenshots/paged-knowledge-0.7.2.png`
* `docs/evidence/screenshots/paged-capabilities-0.7.2.png`

## Version 0.7.1

* `docs/evidence/FRONTEND_DESIGN_FINAL_RECEIPT.md`
* `docs/evidence/screenshots/onehr-design-0.7.1.png`
* `docs/evidence/screenshots/onehr-design-console-0.7.1.png`

## Version 0.7.0

* `docs/evidence/SELF_LEARNING_FINAL_RECEIPT.md`
* `docs/adr/0009-governed-self-learning.md`
* `backend/tests/test_capabilities.py`
* `docs/evidence/screenshots/self-learning-0.7.0.png`

Version: 0.4.0

| Evidence | Purpose | Result |
|---|---|---|
| `docs/Agent Gateway 建设任务.docx` | Authoritative feature specification | Parsed structurally |
| `docs/architecture.md` | System and Phase 1 design | Reviewed against first-round scope |
| `docs/adr/0001-local-codex-runtime.md` | Runtime and authentication decision | Accepted |
| `backend/tests` | Unit, API, event, failure and migration evidence | 14 passed |
| Pytest coverage report | Executed source coverage | 96.75 percent |
| `docker compose config --quiet` | Compose syntax and interpolation | Passed |
| `docker compose up -d --build` | Image build and service startup | Passed |
| `docker compose ps` | Runtime service health | Three healthy services |
| PostgreSQL `alembic_version` | Applied schema revision | `20260727_0001` |
| PostgreSQL table query | Physical schema | Five expected tables |
| Live `POST /api/v1/tasks` | Task admission | HTTP 202 |
| Live task SSE | Ordered runtime events | Sequences 1 through 6 |
| Local Codex `login status` | Authentication boundary | Logged in using ChatGPT |
| Local Codex help output | Installed capability | app-server and exec JSON available |
| `docs/adr/0003-project-registry-and-task-workspaces.md` | Phase 2 identity and isolation decision | Accepted |
| `backend/tests` | Phase 2 backend behavior | 18 passed, 94.05 percent coverage |
| `frontend/src/App.test.tsx` | Task console component behavior | 3 passed |
| Frontend production build | TypeScript and Vite output | Passed |
| Project API smoke | YAML registry exposed through HTTP | Configured `cag` project returned |
| Live workspace isolation | Two task clones | Distinct workspace IDs |
| Live Phase 2 SSE | Ordered lifecycle | Sequences 1 through 8 |
| `docs/evidence/screenshots/phase2-task-completed.png` | Browser task console | Completed task and report visible |
| Browser console | UI runtime diagnostics | Zero warnings and errors |
| `docs/evidence/phase2_test_results.md` | Phase 2 acceptance record | Passed |
| Generated installed app-server schemas | Current local protocol contract | Inspected |
| `backend/tests/test_codex_app_server_runtime.py` | Protocol mapping and auth enforcement | Passed |
| Direct local app-server turn | ChatGPT subscription execution | Completed |
| Live Gateway local Codex task | HTTP through workspace and app-server | Completed |
| `docs/adr/0004-app-server-chatgpt-runtime.md` | Phase 3 runtime decision | Accepted |
| `docs/evidence/phase3_test_results.md` | Phase 3 acceptance record | Passed |
| `docs/adr/0005-cag-conversation-sse-and-self-improvement.md` | Conversation, SSE and candidate boundary | Accepted |
| `backend/tests/test_conversations_api.py` | Persistent Conversation and SSE behavior | Passed |
| `frontend/src/App.test.tsx` | Continuous Conversation UI and EventSource reuse | Passed |
| Live two-turn local subscription smoke | Stored and recalled a random marker | Passed |
| CAG Conversation SSE resume | IDs 9 through 16 after cursor 8 | Passed |
| `docs/self-improvement.md` | Candidate, evaluation, approval and rollback design | Reviewed |
| `docs/evidence/phase4_test_results.md` | 0.4.0 acceptance record | Passed |
| `docs/evidence/screenshots/phase4-continuous-conversation.png` | Two-turn Conversation UI | Visually verified |
| Browser console | Frontend runtime diagnostics | Zero warnings and errors |
| PostgreSQL `alembic_version` | 0.4.0 schema | `20260727_0004` |
| `docs/adr/0006-truthful-runtime-feedback.md` | Backend ledger and frontend projection decision | Accepted |
| `backend/tests/test_codex_app_server_runtime.py` | Visible app-server notification mapping | Passed |
| `backend/tests/test_conversations_api.py` | SSE preservation of every feedback delta | Passed |
| `frontend/src/App.test.tsx` | Feedback levels, row limits and live answer projection | 5 passed |
| Real local Codex Conversation | User-visible runtime feedback | 197 events, 188 Agent deltas |
| CAG Conversation SSE resume | Replay after `Last-Event-ID: 189` | IDs 190 through 197 |
| Browser feedback controls | Full and limited projections | 197 rows and 20 rows |
| Browser console | Truthful feedback runtime diagnostics | Zero errors |
| `docs/evidence/truthful_feedback_test_results.md` | Truthful feedback acceptance record | Passed |
| `docs/adr/0007-governed-enterprise-rag.md` | Enterprise knowledge ownership and scope decision | Accepted |
| `backend/tests/test_knowledge.py` | Encryption, ingestion, search, injection and governance | Passed |
| PostgreSQL `pg_extension` | pgvector runtime | 0.8.2 |
| PostgreSQL HNSW index | 1024 dimensional knowledge vectors | Present |
| Managed Ollama container | Private listener and pinned image | 0.23.3 |
| Real local Ollama RAG smoke | Ingestion, search, citation and memory | Passed |
| `docs/evidence/enterprise_knowledge_test_results.md` | 0.5.0 acceptance record | Passed |
| `docs/agent-harness.md` | 0.6.0 Harness architecture and policy boundary | Implemented |
| `docs/adr/0008-governed-parallel-agent-harness.md` | Parallel role and single writer decision | Accepted |
| `docs/evidence/agent_harness_test_results.md` | 0.6.0 automated acceptance | Passed |
| `docs/evidence/AGENT_HARNESS_FINAL_RECEIPT.md` | 0.6.0 release receipt | Passed |
| `docs/evidence/screenshots/agent-harness-0.6.0.png` | Balanced Harness browser acceptance | Passed |
