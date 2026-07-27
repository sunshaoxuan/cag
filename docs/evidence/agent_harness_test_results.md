# Agent Harness 0.6.0 test results

Date: 2026-07-27

## Automated evidence

* Backend: 47 passed.
* Backend coverage: 87.72 percent.
* Frontend: 5 passed.
* Frontend production build: passed.
* Alembic SQLite upgrade: passed through revision `20260727_0006a`.
* Browser console: zero warnings and errors.
* Browser screenshot: `docs/evidence/screenshots/agent-harness-0.6.0.png`.

## Covered controls

* Fast and balanced role graphs.
* Three parallel investigation slots.
* Independent read-only investigator workspaces.
* Unique Executor write role.
* AgentRun and AgentArtifact persistence.
* Unified Task SSE with parent sequence.
* Safe, approval-required and forbidden command decisions.
* Persistent approval resolution and duplicate-resolution rejection.
* Independent review summary and QualityScore.
* Repeated knowledge ingestion writes zero new vectors and retains one document and chunk.

All automated Agent calls use FakeAgentRuntime and consume no Codex subscription quota.
