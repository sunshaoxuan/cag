# Requirements matrix

Specification source: `docs/Agent Gateway 建设任务.docx`

Legend:

* Implemented: code and tests exist.
* Partial: foundation exists and named acceptance work remains.
* Planned: no implementation claim.

## Phase status

| Requirement | Status for 0.1.0 | Evidence |
|---|---|---|
| Repository and documented architecture | Implemented | `docs/architecture.md` |
| API documentation | Implemented | `docs/api.md` |
| Security documentation | Implemented | `docs/security.md` |
| Phase 1 backend skeleton | Implemented | `backend/app` |
| Database and migrations | Implemented | `backend/app/models`, `backend/alembic` |
| Fake Agent Runtime | Implemented | `backend/app/runtimes/fake.py` |
| Create task API | Implemented | `POST /api/v1/tasks` |
| Query task API | Implemented | `GET /api/v1/tasks/{task_id}` |
| Read task events through SSE | Implemented | `GET /api/v1/tasks/{task_id}/events` |
| Docker Compose | Implemented | `docker-compose.yml` |
| Unit and API tests | Implemented | `backend/tests` |
| Isolated Git workspace | Planned for Phase 2 | Acceptance test required |
| Project YAML loader | Planned for Phase 2 | Acceptance test required |
| Frontend task page | Planned for Phase 2 | Browser and screenshot validation required |
| Local Codex app-server runtime | Planned for Phase 3 | Live subscription smoke test required |
| Skill discovery | Planned for Phase 4 | Selection and lazy-load tests required |
| Runtime Profiles | Planned for Phase 4 | Permission intersection tests required |
| Command Policy Engine | Planned for Phase 4 | Safe, approval and forbidden tests required |
| Approval workflow | Planned for Phase 5 | Pause and resume tests required |
| Git diff and artifacts | Planned for Phase 5 | Artifact integrity tests required |
| MCP client | Planned for Phase 6 | Fake MCP and authorized live smoke tests required |
| Skill proposals and evaluation | Planned for Phase 7 | Human approval gate tests required |
| Complete required data model | Partial | Project, Conversation, Task and TaskEvent exist |
| Authentication and project authorization | Planned | Production blocker |
| Rate and concurrency limits | Planned | Production blocker |
| Secret scanning | Planned | Production blocker |
| OpenTelemetry tracing | Planned | Compatibility test required |

## First-round acceptance

| First-round item | Expected proof |
|---|---|
| Check repository | Investigation report and evidence index |
| Create architecture.md | File review |
| Create api.md | File review and OpenAPI tests |
| Create security.md | File review |
| Establish Phase 1 skeleton | Import and health tests |
| Implement Fake Runtime | Deterministic runtime unit test |
| Create, query and event endpoints | API integration tests |
| Provide Docker Compose | `docker compose config` and service health |
| Write and run tests | Test result record |
| Output files, commands and results | Final receipt |
