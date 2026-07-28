# Final receipt

Release: 0.10.0

## Scope

Durable knowledge source registry, scheduled full snapshot comparison,
incremental vector indexing, lease coordination, failure retry, restart recovery
and source run history.

## Acceptance status

Automated backend and frontend checks pass. The live SQLite database is at
Alembic revision `20260728_0010`. The host Gateway reports version 0.10.0,
Ollama readiness and a running ten second scheduler poll loop.

The existing idempotency evidence source now uses scheduled synchronization
every 15 minutes. A first automatic run wrote one changed file. The following
two automatic runs wrote zero chunks, reported one unchanged file and reused
one stored vector. The source response retained the next due time and last
content change time.

The deployed Knowledge page displays the persistent source registry, automatic
monitor state, schedule, incremental counters and mixed manual and automatic
run history. Browser console validation found zero warnings and errors.

## Safe migration

Existing source rows receive `sync_mode=manual`, a 60 minute stored interval and
no next due time. Existing indexed documents and ingestion history remain
unchanged. Operators choose scheduled mode per existing source.

## Rollback

1. Disable `AGENT_GATEWAY_KNOWLEDGE_SCHEDULER_ENABLED`.
2. Restore application version 0.9.1.
3. Back up the database.
4. Downgrade Alembic to `20260728_0009` if scheduling state no longer needs to
   be retained.

No formal Skill, project rule or Validator was installed. A candidate validator
and task learning receipt were written under
`D:\workspace\codex-selfimp\outputs\cag-durable-knowledge-sync-20260728`.
