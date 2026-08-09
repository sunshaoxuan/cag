# Final acceptance checklist

| Original intent | Result | Evidence |
|---|---|---|
| A healthy long task keeps running | Passed | Aggregate deadline removed; QueueItem lease and document timeout contracts |
| Every document reports independently | Passed | Document terminal checkpoints and public `task.progress` events |
| External monitor can distinguish progress from a stall | Passed | Executing card action count and live task sequence growth |
| One failed document does not fail the parent | Passed | Partial extraction regression test |
| Worker death remains recoverable | Passed | Durable parent QueueItem lease and persisted child checkpoints |
| Running API exposes current progress | Passed | Real 452-document response and API test |
| Required code, docs, version and changelog are updated | Passed | Repository diff and ADR 0029 |
| Backend and frontend tests pass | Passed | `test_results.md` |
| Changed UI passes Browser, Console and screenshot checks | Passed | `audit-active-progress.png`, `audit-completed-progress.png`, zero Console warning or error |
| Historical SSE replay does not create a Task-list request storm | Passed | Single-flight regression assertion and completed-state reload Browser check |
| Real production extraction reaches final aggregation | Passed | Extraction `5cd11502-565f-4ec6-949a-539112cbfb7b` reached `review_required` and `EXTRACTION_PARTIAL` after aggregation in 5 minutes 29 seconds |
| Every production manifest child reaches one public terminal report | Passed | 452 terminal document events: 128 extracted, 285 failed, 39 excluded |
| Parent publishes a complete externally observable lifecycle | Passed | 458 events: 1 created, 1 started, 455 progress, 1 completed; last global sequence 14712 |
| Version is running on the intended host boundary | Passed | Host API `/health/ready` reports 0.27.0 ready; Docker frontend is healthy; no Docker Gateway container |
