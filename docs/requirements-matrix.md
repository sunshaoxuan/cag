# Requirements matrix

Specification source: `docs/Agent Gateway 建设任务.docx`

Legend:

* Implemented: code and tests exist.
* Partial: foundation exists and named acceptance work remains.
* Planned: no implementation claim.

## Phase status

| Requirement | Status for 0.12.0 | Evidence |
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
| Gateway all-interface listener | Implemented | Host runner, managed task listener validation and Compose port publication |
| Unit and API tests | Implemented | `backend/tests` |
| Isolated Git workspace | Implemented | Distinct workspace test and Compose smoke |
| Project YAML loader | Implemented | Project registry tests and live Project API |
| Frontend task page | Implemented | Component tests, production build, browser and screenshot evidence |
| Unified visual management console | Implemented | Port 5173 overview, API test, audit, knowledge and capability routes |
| Same-origin management API and SSE | Implemented | Frontend Nginx `/api` proxy and LAN browser validation |
| OneHR design language frontend | Implemented | `docs/frontend-design.md`, responsive CSS, browser screenshot and console evidence |
| Routed frontend information architecture | Implemented | `/`, `/conversation`, `/audit`, `/knowledge`, `/capabilities`, route isolation tests and browser evidence |
| External task API trace contract | Implemented | Trace ID, client request ID, request hash, source and idempotency tests |
| Global API action audit stream | Implemented | Global TaskEvent sequence, `/api/v1/audit/events`, resume and filter tests |
| API monitoring frontend | Implemented | `/audit`, live SSE projection, component and browser evidence |
| Local Codex app-server runtime | Implemented | Fake protocol tests and live subscription Gateway smoke |
| Conversation create and query API | Implemented | `POST` and `GET /api/v1/conversations` |
| Persistent Codex conversation history | Implemented | `thread/start`, stored thread ID and `thread/resume` live smoke |
| CAG-owned multi-turn SSE | Implemented | Conversation event sequence, heartbeat and resume tests |
| Continuous conversation frontend | Implemented | Component, build and browser evidence |
| Truthful runtime feedback | Implemented | User-visible app-server deltas are durable CAG events; hidden reasoning and credentials remain excluded |
| Enterprise knowledge plane | Implemented | `docs/enterprise-knowledge.md`, knowledge API tests |
| Managed local, UNC, Git, GitLab and SVN knowledge sources | Implemented | Connector tests, `docs/knowledge-source-api.md`, Knowledge page browser evidence |
| Source credential isolation | Implemented | Credential store contract, Git environment header and SVN stdin tests; live authenticated UNC acceptance requires a target share |
| Managed credential reveal and copy | Implemented | explicit no-store reveal API, Windows Credential Manager lookup, frontend display and copy tests |
| Source collection stage SSE | Implemented | Durable collection, cleaning, indexing and Source Memory events |
| Scalable folder traversal feedback | Implemented | Breadth-first directory queue, per-directory progress SSE, single-flight guard and browser evidence |
| Local Ollama embedding and memory models | Implemented | Ollama adapter tests and local benchmark evidence |
| Tenant and ProductVersion knowledge isolation | Implemented | UUID foreign keys and filtered retrieval tests |
| Governed Modular RAG | Implemented | Ingestion, hybrid recall, citations and context isolation |
| Standards control mapping | Implemented | `docs/standards-control-matrix.md`, `GET /api/v1/standards/controls` |
| Frontend feedback projection | Implemented | Key, standard and full detail with a configurable visible-row limit |
| Skill discovery | Implemented | Gateway capability registry and seeded Skill catalog |
| Runtime Profiles | Implemented | Project allowlist, Harness Profile and permission intersection |
| Command Policy Engine | Implemented | `backend/app/policies/command_policy.py`, policy tests |
| Approval workflow | Implemented | `ApprovalRequest`, resolve API and runtime callback tests |
| Agent Harness | Implemented | `backend/app/harness`, fast and balanced tests |
| Parallel read-only investigation and single writer | Implemented | distinct investigator clones and Executor access mode |
| Structured Agent artifacts | Implemented | `AgentArtifact` SHA 256 record and API tests |
| Unified Harness SSE | Implemented | parent TaskEvent sequence and Harness event tests |
| Idempotent vector indexing | Implemented | source fingerprint, path and ordinal uniqueness, vector reuse test |
| Durable knowledge source registry and scheduled rescan | Implemented | persisted sync policy, database lease, retry state, restart recovery, run history and scheduler tests |
| Git diff and artifacts | Partial | structured Agent artifacts implemented, normalized Git diff artifact remains planned |
| MCP client | Planned for Phase 6 | Fake MCP and authorized live smoke tests required |
| Skill proposals and evaluation | Implemented | CapabilityAsset, CapabilityEvaluation and promotion API tests |
| Shadow, canary and automatic rollback | Implemented | ten shadow and five canary gates, rollback tests and receipts |
| Learning trigger pipeline | Implemented | durable LearningSignal and repeated pattern candidate test |
| Daily capability gardeners | Implemented | Doc, Skill, Tool and Memory Gardener records |
| Complete required data model | Implemented | knowledge, Harness, learning, promotion, rollback and control entities |
| Authentication and project authorization | Planned | Production blocker |
| Rate and concurrency limits | Partial | Harness concurrency limit implemented, distributed rate limiting remains |
| Secret scanning | Implemented | knowledge and capability proposal scanners |
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
