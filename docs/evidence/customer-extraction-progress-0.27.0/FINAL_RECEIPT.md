# CAG 0.27.0 final receipt

## Delivered

Customer extraction now waits while its worker and document children continue
to report progress. Every manifest document has a durable terminal checkpoint
and a public Generic Task event. Parent aggregation is independent from total
wall-clock runtime, while each Ollama document request remains bounded.

## Verification

* Backend: 162 passed, 3 skipped, coverage 85.43 percent.
* Frontend: 17 passed and production build passed.
* Runtime: CAG 0.27.0, PostgreSQL and Redis ready, one extraction worker.
* Browser: reload restored the completed 458-action card; Console warning and
  error count was zero; active and completed screenshots were recorded.
* Production terminal result: `review_required` with `EXTRACTION_PARTIAL` after
  final aggregation in 5 minutes 29 seconds.
* Coverage: 452 total, 134 ready, 128 analyzed, 285 failed, 39 excluded,
  coverage rate 0.309927.
* Public lifecycle: 458 events, including exactly 452 document terminal events.

The `review_required` state is the designed aggregated result for partial
source coverage. It is a completed Generic Task and is distinct from the former
900 second parent failure.

## Rollback

Restore the prior Git revision and version 0.26.0, restart the scheduled
Gateway and verify queue leases. Existing document checkpoints and Task events
remain audit records and must not be deleted.
