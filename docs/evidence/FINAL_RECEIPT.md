# Current release receipt

Version: 0.4.0

Date: 2026-07-27

Branch: `master`

## Delivered

* Local ChatGPT-authenticated Codex app-server execution.
* CAG Conversation API and persistent internal Codex thread mapping.
* CAG-owned multi-turn SSE with continuous event IDs and reconnection.
* Continuous Conversation frontend.
* Isolated Git workspace per Task.
* Runtime Profile allowlist.
* Restricted self-improvement candidate path.
* Tests, migrations, architecture, API, security, deployment and evidence.

## Verified

* 36 backend tests passed with 91.06 percent coverage.
* 3 frontend tests and production build passed.
* Real two-turn Codex context resume passed.
* Real self-improvement candidate writing passed.
* Four Compose services are healthy.
* PostgreSQL migration head is `20260727_0004`.
* Browser two-turn flow passed with zero console warnings or errors.

## Open production gates

Authentication, project authorization, rate limiting, durable queueing, cancellation, complete concurrency control, command policy, approval persistence, Secret Scanner, immutable audit and formal Skill installation remain planned.

## Rollback

Stop the 0.4.0 services, deploy the prior release commit and retain named volumes. Downgrade Alembic only when the 0.4.0 Conversation event schema must be removed. Candidate directories and Codex thread history stay retained until an operator approves deletion.
