# Version 0.17.0 final receipt

## Delivered

* PostgreSQL authoritative interactive and knowledge queues.
* Redis Pub/Sub wake notifications with PostgreSQL polling fallback.
* Lease recovery, worker heartbeat, finite retry, cancellation and status APIs.
* Same-Conversation serialization and cross-Conversation concurrency.
* Online API reference with PowerShell, curl and JavaScript examples.
* Guarded SQLite to PostgreSQL cutover with database migration receipts.
* First-restart frontend rebuild for the 5173 management console.

## Cutover boundary

The 0.17.0 release does not stop the active 0.12.0 process. After that process
finishes naturally, the next managed start performs Alembic upgrade, verifies
that legacy work is terminal, migrates data, writes a receipt, checks Redis,
refreshes the frontend without starting Compose Gateway, and starts the host
Gateway on all IPv4 interfaces.

If active work remains, cutover exits before modifying PostgreSQL application
data. The legacy SQLite file is retained after a successful migration.

## Rollback

Stop the 0.17.0 host workers, retain PostgreSQL and migration receipts, restore
the previous deployment and keep the legacy SQLite source offline for
comparison. The frontend container can be restored from the previous release
image independently of PostgreSQL.

## Acceptance

Backend, frontend, PowerShell, Compose, real PostgreSQL, real Redis and browser
checks passed. The release screenshot is
`docs/evidence/screenshots/durable-queue-api-docs-0.17.0.png`.
