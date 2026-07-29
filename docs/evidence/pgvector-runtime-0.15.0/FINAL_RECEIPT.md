# Version 0.15.0 final receipt

## Delivered

* PostgreSQL 16 plus pgvector as the required managed runtime database.
* Database-native cosine vector ranking through the HNSW index.
* SQLite rejection in every managed application environment.
* Controlled one-time complete migration with dry run, apply gate and receipts.
* Local-only PostgreSQL port publication for the trusted Windows host Gateway.
* Real pgvector query, migration and container readiness evidence.

## Deferred live action

The current 0.12.0 knowledge ingestion is still running. Its process was not
stopped or restarted. Production-sized migration and the 8000 service cutover
must wait for that ingestion to reach a terminal state.

The live migration preflight produced a blocked receipt and made no target
connection.

## Acceptance

The release is accepted for source delivery and later cutover. The live runtime
continues on its existing database until the controlled migration is executed.

## Rollback

Revert the 0.15.0 release commit before cutover. After cutover, stop the
PostgreSQL-backed Gateway, retain its database and receipt, and restore the
offline legacy database with the pre-cutover application version.
