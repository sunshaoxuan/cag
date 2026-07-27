# Requirements matrix

Specification source: `docs/Agent Gateway 建设任务.docx`

Legend:

* Implemented: code and tests exist.
* Partial: foundation exists and named acceptance work remains.
* Planned: no implementation claim.

## Phase status

| Requirement | Status for 0.4.0 | Evidence |
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
| Isolated Git workspace | Implemented | Distinct workspace test and Compose smoke |
| Project YAML loader | Implemented | Project registry tests and live Project API |
| Frontend task page | Implemented | Component tests, production build, browser and screenshot evidence |
| Local Codex app-server runtime | Implemented | Fake protocol tests and live subscription Gateway smoke |
| Conversation create and query API | Implemented | `POST` and `GET /api/v1/conversations` |
| Persistent Codex conversation history | Implemented | `thread/start`, stored thread ID and `thread/resume` live smoke |
| CAG-owned multi-turn SSE | Implemented | Conversation event sequence, heartbeat and resume tests |
| Continuous conversation frontend | Implemented | Component, build and browser evidence |
| Truthful runtime feedback | Implemented | User-visible app-server deltas are durable CAG events; hidden reasoning and credentials remain excluded |
| Frontend feedback projection | Implemented | Key, standard and full detail with a configurable visible-row limit |
| Skill discovery | Planned for Phase 4 | Selection and lazy-load tests required |
| Runtime Profiles | Partial | Project allowlist and restricted candidate profile implemented; complete permission intersection remains |
| Command Policy Engine | Planned for Phase 4 | Safe, approval and forbidden tests required |
| Approval workflow | Planned for Phase 5 | Pause and resume tests required |
| Git diff and artifacts | Planned for Phase 5 | Artifact integrity tests required |
| MCP client | Planned for Phase 6 | Fake MCP and authorized live smoke tests required |
| Skill proposals and evaluation | Partial | Restricted candidate output path implemented; durable proposal and evaluation records remain |
| Complete required data model | Partial | Project, Conversation, Task and TaskEvent exist; later phase models remain |
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
