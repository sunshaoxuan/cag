# Phase 4 persistent conversation receipt

Version: 0.4.0

Date: 2026-07-27

Branch: `master`

## Delivered

* Caller-visible CAG Conversation API.
* Internal persistent Codex thread mapping.
* CAG-owned multi-turn SSE with heartbeat and resume.
* Continuous conversation frontend.
* Runtime Profile allowlist validation.
* Restricted self-improvement candidate path.
* Architecture, API, security, deployment, ADR and self-improvement documentation.

## Runtime boundary

The Gateway invokes the locally installed Codex app-server through the existing ChatGPT subscription login. The frontend and external callers communicate only with CAG HTTP and SSE endpoints.

## Acceptance

Persistent two-turn local subscription execution: Passed.

CAG Conversation SSE continuity: Passed.

Automated backend and frontend validation: Passed.

Restricted self-improvement candidate writing: Passed.

Browser and container closure: Passed.

The Compose database is at Alembic revision `20260727_0004`. Four services are healthy. The browser completed two turns through one CAG Conversation, displayed continuous event IDs 1 through 16, produced no console warnings or errors, and generated the Phase 4 screenshot.

## Rollback

1. Stop the 0.4.0 Gateway.
2. Deploy the prior release commit.
3. Run Alembic downgrade to `20260727_0002` only when removal of 0.4.0 Conversation columns and event sequencing is required.
4. Retain Codex local thread history and `codex-selfimp` candidate directories until an operator approves deletion.
