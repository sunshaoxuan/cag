# Evidence index

| Claim | Evidence | Confidence | Limitation |
| --- | --- | --- | --- |
| API and worker are isolated | `/health/ready` role `api`, listener PID differs from QueueWorker PID, `backend/tests/test_process_isolation.py` | high | Worker rows remain visible until heartbeat cutoff after a forced stop |
| Redis wake channel works across processes | Production readiness `redis_connected=true`, API notifier lifecycle test | high | PostgreSQL polling remains the recovery path during Redis outage |
| Customer exact path wins ranking | Production fast searches for Code and official name, `exact_path` reason | high | Ranking depends on an ingested customer directory containing the identity value |
| Retrieval cost is bounded | `backend/app/knowledge/service.py`, Migration 0021, PostgreSQL boundary tests | high | Database load still depends on configured candidate and timeout values |
| Structured extraction is citation gated | Completed production Task `a109cff6-8c7f-467d-b8d8-da4699693ea2`, forged citation unit test | high | Candidate completeness depends on learned source content |
| Cancellation is deterministic | Production Task `6206ece4-284f-4d27-89dc-a6469f3f5080`, Queue timestamp race test | high | Cancellation can retain already committed ingestion generations for audit |
| Scheduled cancellation does not immediately recreate work | Source next sync moved one interval and scheduler claim returned false in regression test | high | The source becomes due again at its configured next sync time |
| Release artifacts are buildable | Backend, frontend, Pester, Compose and Docker build results | high | Runtime browser evidence is recorded separately in this directory |

## Primary implementation paths

* `backend/app/worker.py`
* `backend/app/main.py`
* `backend/app/knowledge/service.py`
* `backend/app/knowledge/extraction.py`
* `backend/app/queue/service.py`
* `backend/alembic/versions/20260806_0021_bounded_knowledge_search.py`
* `scripts/run-local-codex-gateway.ps1`
* `docs/adr/0025-isolated-bounded-knowledge-retrieval.md`
