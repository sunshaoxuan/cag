# ADR 0029: Customer extraction progress and liveness

## Status

Accepted for version 0.27.0 and amended for version 0.28.0.

## Context

The scoped extraction for organization `0276` resolved the correct Catalog
scope and continued completing documents until six seconds before failure. The
manifest contained 452 documents and 134 ready documents. Eighty documents
were analyzed before the fixed 900 second aggregate deadline converted the
healthy task into `EXTRACTION_FAILED` with stage `overall_deadline`.

The extraction stored 87 internal events while its Generic Task exposed only
`task.created`. External API monitoring could not distinguish continuing work
from a stalled task. One QueueItem represented the parent extraction, while
the existing `KnowledgeExtractionTaskDocument` rows already provided physical
child identities, status and checkpoints.

Mature durable workflow systems separate an activity heartbeat timeout from a
request timeout. AWS Step Functions documents heartbeats as proof that a task
is still running and needs more time, while task-specific calls retain bounded
timeouts. CAG already has the equivalent durable QueueItem lease and heartbeat.

## Decision

1. Remove the fixed aggregate customer extraction deadline and its environment
   setting.
2. Use the QueueItem heartbeat and expiring lease as worker-liveness evidence.
3. Stream every per-document Ollama response. Treat the configured 300 second
   value as stream inactivity timeout. Every received NDJSON chunk refreshes
   document activity, so continuing generation has no fixed total deadline.
4. Treat every `KnowledgeExtractionTaskDocument` as a durable child work item.
5. Commit a throttled `document.model.activity` checkpoint while a model is
   responding, followed by one terminal checkpoint for every analyzed, failed
   or excluded child.
6. Publish every child terminal transition to the Generic Task as
   `task.progress`, including the child physical ID, ordinal, total and result.
7. Publish scope, manifest and aggregation transitions through the same Generic
   Task stream. Map extraction start, completion and failure to standard Task
   event types.
8. Return persisted progress counters and `last_progress_at` while the parent
   task is active.
9. Aggregate only after every manifest child has a terminal state.
10. On worker loss, let the queue lease recover the parent and continue from
    existing child checkpoints.

## Consequences

Large customer scopes can run for the time required by their document count
while active progress remains visible. A model stream that produces no data for
the configured inactivity interval is bounded at the document boundary. A dead worker stops renewing its lease and another
worker can continue the same physical parent task. The audit stream receives
one event per document outcome, so event volume scales with manifest size and
remains governed by existing sequence pagination and frontend display limits.

## Acceptance

1. A test extraction completes after a legacy aggregate deadline value has
   already elapsed.
2. Every manifest document produces one public terminal progress event, and
   active model streams produce throttled per-document activity events.
3. Successful, model-failed, metadata-only and excluded documents all report
   their physical child ID and ordinal.
4. Running extraction responses expose persisted counters and last progress.
5. Generic Task events contain `task.started`, `task.progress` and
   `task.completed` for a successful partial extraction.
6. The API monitoring frontend renders `task.progress` and advances the task
   sequence.
7. A production scan that formerly failed at the aggregate deadline keeps
   reporting every document and reaches aggregation while its worker is live.
8. Historical audit replay shares an in-flight Task-list refresh instead of
   issuing one request for every event whose Task is not loaded yet.
9. Cancelling an active extraction sets both its QueueItem and extraction
   record to `cancelled`.

## Rollback

Restore version 0.26.0. Stop the worker, restore the aggregate timeout setting
and restart the runtime. Existing document checkpoints and public Task events
remain valid audit records and must not be deleted.

## References

* AWS Step Functions Task state heartbeat and timeout documentation:
  https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html
* AWS Step Functions `SendTaskHeartbeat` API:
  https://docs.aws.amazon.com/step-functions/latest/apireference/API_SendTaskHeartbeat.html
* Ollama streaming API:
  https://docs.ollama.com/api/streaming
* Ollama generate API:
  https://docs.ollama.com/api/generate
