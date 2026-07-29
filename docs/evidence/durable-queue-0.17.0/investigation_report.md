# One Agent Gateway 0.17.0 durable queue investigation

## Scope

This release replaces in-process admission with a durable PostgreSQL queue,
uses Redis only for wake notifications, adds an online API reference, and
prepares the first restart after the active 0.12.0 learning run for a guarded
SQLite cutover.

## Evidence

| Finding | Evidence | Result |
|---|---|---|
| Accepted tasks previously depended on process-local background execution | Previous task and knowledge API handlers | Restart recovery required a durable owner |
| PostgreSQL can serialize queue claims safely | `queue_items`, row locks and `SKIP LOCKED` | PostgreSQL is the authoritative queue |
| Redis messages do not provide durable delivery | `QueueNotifier` and ADR 0018 | Redis carries wake notifications only |
| Conversation order must remain stable | Correlated earlier-item claim predicate | Same-Conversation tasks are serial |
| Independent users need concurrency | Separate interactive and knowledge worker pools | Different Conversations can execute concurrently |
| Legacy data must remain consistent at cutover | Active-work inspection and transactional replacement | Cutover runs only after active source work finishes |
| The management UI must change on the same restart | Frontend build and `compose up -d --no-deps frontend` | Port 5173 receives the 0.17.0 UI without starting Compose Gateway |

## Runtime boundary

The live process with PID `17348` remained on version `0.12.0`, listened on
`0.0.0.0:8000`, and returned ready during release validation. Validation used
ports `8017` and `5174`, temporary PostgreSQL databases and a temporary Redis
container.

## Decision

PostgreSQL records admission, priority, state, lease, attempts, cancellation
and worker heartbeat. Redis Pub/Sub shortens wake latency. Polling and expired
lease recovery preserve progress when Redis is unavailable.

The automatic cutover calculates the legacy source digest, checks active Agent
and knowledge work, replaces application tables in one PostgreSQL transaction,
validates migrated identities and vectors, and records a database receipt.
Matching receipts make subsequent starts idempotent.
