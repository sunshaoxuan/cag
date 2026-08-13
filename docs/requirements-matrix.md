# Requirements matrix

Specification source: `docs/Agent Gateway 建设任务.docx`

Legend:

* Implemented: code and tests exist.
* Partial: foundation exists and named acceptance work remains.
* Planned: no implementation claim.

## Phase status

| Requirement | Status for 0.28.5 | Evidence |
|---|---|---|
| Repository and documented architecture | Implemented | `docs/architecture.md` |
| API documentation | Implemented | `/api-docs`, `docs/api.md`, component and browser tests |
| LAN HTTP API test console | Implemented | Cryptographically random RFC 4122 v4 request IDs use `crypto.getRandomValues()` in HTTPS, localhost and LAN HTTP browser contexts |
| Security documentation | Implemented | `docs/security.md` |
| Phase 1 backend skeleton | Implemented | `backend/app` |
| Database and migrations | Implemented | `backend/app/models`, `backend/alembic` |
| Fake Agent Runtime | Implemented | `backend/app/runtimes/fake.py` |
| Create task API | Implemented | `POST /api/v1/tasks` |
| Query task API | Implemented | `GET /api/v1/tasks/{task_id}` |
| Task 取消 API | Implemented | `POST /api/v1/tasks/{task_id}/cancel`、Queued 即時取消、Leased 取消要求、終端冪等及び QueueItem 欠落 409 の API 試験 |
| Read task events through SSE | Implemented | `GET /api/v1/tasks/{task_id}/events`, validation Session closes before streaming |
| Docker Compose | Implemented | `docker-compose.yml`, PostgreSQL and Redis `unless-stopped` recovery |
| Gateway all-interface listener | Implemented | Host runner, managed task listener validation and Compose port publication |
| Continuous Windows supervision | Implemented | Startup, sign-in and one-minute watchdog triggers, full readiness monitor, failure retry and rotating supervisor log |
| Unit and API tests | Implemented | `backend/tests` |
| Isolated Git workspace | Implemented | Distinct workspace test and Compose smoke |
| Project YAML loader | Implemented | Project registry tests and live Project API |
| Frontend task page | Implemented | Component tests, production build, browser and screenshot evidence |
| Unified visual management console | Implemented | Port 5173 overview, API test, audit, knowledge, code knowledge and capability routes; code knowledge search controls share a common 50px control height |
| Same-origin management API and SSE | Implemented | Frontend Nginx `/api` proxy and LAN browser validation |
| OneHR design language frontend | Implemented | `docs/frontend-design.md`, responsive CSS, browser screenshot and console evidence |
| Routed frontend information architecture | Implemented | `/`, `/conversation`, `/audit`, `/knowledge`, `/code-knowledge`, `/memory`, `/capabilities`, route isolation tests and browser evidence |
| External task API trace contract | Implemented | Trace ID, client request ID, request hash, source and idempotency tests |
| Global API action audit stream | Implemented | Global TaskEvent sequence, `/api/v1/audit/events`, resume and filter tests |
| PostgreSQL plus Redis durable gateway queue | Implemented | QueueItem, QueueWorker, `FOR UPDATE SKIP LOCKED`, Redis wake, lease recovery and queue API tests |
| API and queue worker process isolation | Implemented | `app.worker`, host dual-process launcher, API-only Redis notifier lifecycle test and ADR 0025 |
| Separate interactive, ingestion, customer extraction and operations worker pools | Implemented | Worker-process QueueCoordinator pools, queue status API, extraction bootstrap recovery and interactive plus extraction completion during delayed knowledge ingestion |
| Durable self-operations issue queue | Implemented | `OperationalIssue`, `QueueItem.issue_id`, operations Worker and queue recovery tests |
| Universal operational failure intake | Implemented | Task, ingestion, API, supervisor spool and public intake API |
| AI boundary, planning and independent Review | Implemented | read-only triage and Review runtime phases, sequence-addressed fresh workspaces, versioned artifacts and tests |
| Structured operational decision brief | Implemented | strict planner and reviewer schemas, resolution mode, root cause, proposed changes, blockers, validation and rollback |
| Simplified Chinese operational decisions | Implemented | `administrator_language: zh-CN`, prompt and developer instruction constraints, Chinese field validation, planning failure brief and fail-closed fallback |
| Fail-closed operational approval | Implemented | malformed, incomplete, revise or blocked Reviews enter `plan_revision_required`; approval repeats the gate server-side |
| Administrator improvement approval | Implemented | top-of-detail decision panel, approval, revision, no-modification rejection and authenticated audit APIs |
| Authenticated operations administration | Implemented | constant-time administrator token validation, authenticated identity audit and session-scoped UI credentials |
| Bounded operational AI timeline | Implemented | completed runtime evidence is durable; cumulative `*.delta` events are excluded; issue detail omits events and `/operations/issues/{id}/events` provides bounded sequence pagination |
| Governed improvement branch | Implemented | approved internal issues create isolated `codex/improvement/<issue-code>` task branches |
| Improvement re-evaluation and closure | Implemented | AI evaluation Worker, original issue evidence, pass closure, failed-cycle resubmission and fresh Queue Item regression test |
| Visual self-operations management | Implemented | `/operations` top decision panel, occurrence-independent authority, server-authoritative actions, stale-response protection, issue-scoped forms, inline mutation feedback and paginated evidence timeline |
| Same Conversation serial execution | Implemented | Conversation claim ordering and multiple submission tests |
| API monitoring frontend | Implemented | `/audit`, live SSE projection, component and browser evidence |
| Local Codex app-server runtime | Implemented | Fake protocol tests, ChatGPT and API Key account/read tests, live local app-server verification |
| Conversation create and query API | Implemented | `POST` and `GET /api/v1/conversations`, client-scoped idempotent replay and request-hash conflict tests |
| OneOps resilient Task routing contract | Implemented | `SIMPLE` and `GENERAL` tier validation, model and effort consistency, OneOps v3 routing payload persistence tests |
| Persistent Codex conversation history | Implemented | `thread/start`, stored thread ID and `thread/resume` live smoke |
| CAG-owned multi-turn SSE | Implemented | Conversation event sequence, heartbeat, resume and bounded validation Session tests |
| Knowledge-first Conversation execution | Implemented | pre-runtime retrieval, bounded fragments, resource URI injection and Conversation SSE tests |
| Traceable knowledge learning loop | Implemented | citations shared by context injection, final report and MemoryCandidate evidence |
| Continuous conversation frontend | Implemented | Component, build and browser evidence |
| Truthful runtime feedback | Implemented | User-visible app-server deltas are durable CAG events; hidden reasoning and credentials remain excluded |
| Conversation intermediate-answer presentation | Implemented | Agent messages are grouped in a gray, collapsed disclosure while the Task remains active |
| Terminal report Markdown | Implemented | Final report is published after terminal Task state and rendered with GitHub-flavored Markdown |
| Enterprise knowledge plane | Implemented | `docs/enterprise-knowledge.md`, knowledge API tests |
| Managed local, UNC, Git, GitLab and SVN knowledge sources | Implemented | Connector tests, `docs/knowledge-source-api.md`, Knowledge page browser evidence |
| Visual knowledge source lifecycle management | Implemented | Source create, edit, enable, disable, search, filter, trigger, live run center and history controls |
| Source credential isolation | Implemented | Credential store contract, Git environment header and SVN stdin tests; live authenticated UNC acceptance requires a target share |
| Managed credential reveal and copy | Implemented | explicit no-store reveal API, Windows Credential Manager lookup, frontend display and copy tests |
| Source collection stage SSE | Implemented | Durable collection, cleaning, indexing and Source Memory events |
| Scalable folder traversal feedback | Implemented | Breadth-first directory queue, per-directory progress SSE, single-flight guard and browser evidence |
| File-level ingestion rejection audit | Implemented | Durable path and reason records, paged API, CSV export, gzip JSONL archive and retention tests |
| Durable knowledge source entry inventory | Implemented | `KnowledgeSourceEntry`, path search and pagination API, processor evidence, management table and migration tests |
| Policy-routed knowledge processing | Implemented | Metadata-only archive and dump routing, temporary Office filtering, path-only empty files, Shell Link target observation, semantic XLSX extraction and structural code routing tests |
| Processor policy reprocessing | Implemented | Processor fingerprints, legacy code backfill and unchanged document vector reuse tests |
| 64-bit knowledge file sizes | Implemented | PostgreSQL `BIGINT` migration and sparse large-file ingestion test |
| Resumable knowledge ingestion queue | Implemented | Knowledge ingestion jobs use PostgreSQL leases, Redis wake, cancellation and restart recovery |
| Post-start lease expiry recovery | Implemented | each queue claim transaction requeues expired leases for its queue and resumes durable checkpoints |
| Per-file parallel knowledge work items | Planned | ADR 0015; file-level claim, pause and checkpoint tests required |
| Path-complete semantic indexing | Implemented | Every readable physical file retains raw SHA 256 and path evidence before processing policy; supported files up to 100 MB are cleaned; canonical path and redacted content share one multilingual embedding representation; duplicate content does not remove paths |
| Managed PostgreSQL and pgvector host runtime | Implemented | Runtime gate, native vector query, Docker restart recovery, guarded automatic cutover, database receipt and live 170807-vector verification |
| Local Ollama embedding and memory models | Implemented | Ollama adapter tests and local benchmark evidence |
| Tenant and stable Product knowledge isolation | Implemented | Product-scoped retrieval follows the stable Product physical ID across ProductVersion changes |
| Atomic active knowledge generations | Implemented | New vectors and code facts commit in one transaction; failed refreshes preserve the last completed generation |
| Governed Modular RAG | Implemented | Ingestion, hybrid recall, resource-linked citations and context isolation |
| Japanese enterprise text encoding | Implemented | UTF-8, UTF-16, CP932 and Shift-JIS extraction tests |
| Structure-aware code indexing | Implemented | AST and Tree-sitter adapter, language fallback, symbol-boundary chunks and code intelligence tests |
| Code symbol and relationship graph | Implemented | CodeSymbol, CodeRelation, CodeDocumentLink, migration and idempotency tests |
| Code and documentation linkage | Implemented | Deterministic path and symbol evidence, detail API and retrieval graph expansion |
| Multilingual semantic and exact hybrid retrieval | Implemented | Qwen3 path and content embeddings, Japanese, Chinese and English query instruction, exact path and lexical channels, RRF and optional local reranking |
| Bounded indexed knowledge retrieval | Implemented | Separate bounded Chunk text, Document path and Source subpath channels, pg_trgm expression indexes, fixed candidate limits, database statement timeout, profile deadlines and production-scale availability acceptance |
| Cross-script customer path retrieval | Implemented | OpenCC simplified, traditional and Japanese Shinjitai query variants plus per-Document result diversification |
| Current-only ordinary knowledge search | Implemented | Shared historical path policy excludes old, backup and archived Document candidates from every retrieval channel |
| Scoped customer ledger knowledge extraction | Implemented | request schema v1 with analysis Template v2, required-version Scope Repair, Source update isolation, exact current-path Document selection, historical-path exclusion, UNC-safe Shortcut observations, dedicated extraction queue, lease-based liveness, public per-document terminal and model activity progress, stream-inactivity timeout, truthful cancellation, exhaustive manifest, file checkpoints, typed fields, coverage, conflicts, unresolved fields and stable errors |
| Customer customization and remote ledger classification | Implemented | customization schema, field-specific model output schema, shared ingestion and manifest support policy, SQL and XLSM processing, VPN and Environment field contracts, physical-record apply tests |
| Customer ledger evidence and review safety | Implemented | candidate and Knowledge Block physical IDs, Document Version citations, structured locations, redacted excerpts, candidates-only output and no-delete policy |
| Independent processing and business versions | Implemented | Active and Superseded Processing Versions, failed refresh protection, immutable Knowledge Blocks, Applicability Revisions and `analysis_context.as_of` selection |
| Permanent learned knowledge history | Implemented | changed and absent source files retain historical Document Versions, Processing Versions, Blocks and archive Chunks |
| Content-addressed durable evidence objects | Planned | ADR 0032 and `docs/cag-evidence-experience-evolution-roadmap.md`; S3-compatible raw or cleaned Artifact persistence, replicas, integrity and recovery tests required |
| Universal safe text extraction | Planned | MIME, magic and text-likelihood routing plus sandboxed legacy Office, mail, RTF, image OCR, configuration and archive-member extractors required |
| Existing knowledge conversion and atomic rebuild | Planned | Conversion Manifest, reuse, object backfill, reclean, reindex, shadow comparison, atomic Generation activation and rollback evidence required |
| Evidence, experience and Task relation network | Planned | typed contextual relations, applicability, contradiction, supersession, Outbox projection and reverse impact analysis required |
| Approved Experience retrieval and Task feedback | Planned | approved MemoryCandidate indexing, Experience Packet injection, actual-use receipt, outcome revalidation and correction flow required |
| Production graph engine selection | Planned | PostgreSQL adjacency, Apache AGE and independent graph database must use the same million-edge and ten-million-edge benchmark and recovery contract |
| Cancellation precedence and scheduled rescan control | Implemented | pending cancellation is committed before requeue; scheduled cancellation releases the source lease and advances its next due time; both paths have regression tests |
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
| Resumable vector generation | Implemented | redacted-input embeddings use proven 8 Chunk batches, duplicate cache keys are inserted once, checkpoints commit per batch, retries calculate only missing vectors and final knowledge replacement remains atomic |
| End-to-end file provenance | Implemented | raw file SHA 256, resumable bounded-concurrency legacy backfill, cleaned document and chunk hashes, SourceEntry physical foreign key, chunk to file citation reverse lookup and closure audit |
| Shortcut flattening and cycle safety | Implemented | LnkParse3 UNC reconstruction, same-share or allowed-root boundary, logical-path flattening, physical-directory visited gate and target-status tests |
| Durable knowledge source registry and scheduled rescan | Implemented | persisted sync policy, database lease, active-ingestion claim exclusion, Source-row-locked Scheduled Ingestion creation, PostgreSQL concurrency test, retry state, restart recovery and run history |
| Git diff and artifacts | Partial | structured Agent artifacts implemented, normalized Git diff artifact remains planned |
| MCP client | Planned for Phase 6 | Fake MCP and authorized live smoke tests required |
| Skill proposals and evaluation | Implemented | CapabilityAsset, CapabilityEvaluation and promotion API tests |
| Shadow, canary and automatic rollback | Implemented | ten shadow and five canary gates, rollback tests and receipts |
| Learning trigger pipeline | Implemented | durable LearningSignal and repeated pattern candidate test |
| Daily capability gardeners | Implemented | Doc, Skill, Tool and Memory Gardener records |
| Complete required data model | Implemented | knowledge, Harness, learning, promotion, rollback and control entities |
| Authentication and project authorization | Planned | Production blocker |
| Rate and concurrency limits | Partial | Harness concurrency limit implemented, distributed rate limiting remains |
| Multilingual secret scanning | Implemented | English and Japanese credential labels, protected connection targets and credential-bearing URL redaction before search, embedding and model context |
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
