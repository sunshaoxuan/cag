# CAG 0.27.0 customer extraction progress investigation

## Question

Why did OneOps action `4dec6acb-ff69-404e-9682-308f8390cdee` fail while it
was still processing documents, and does the corrected implementation report
every document independently?

## Root cause

The extraction had one parent QueueItem and a fixed 900 second coroutine
deadline. Its worker heartbeat remained healthy and its last successful
document completed six seconds before the deadline. The deadline converted the
whole parent into `EXTRACTION_FAILED` with stage `overall_deadline`.

The failed extraction had 452 manifest rows and 134 ready documents. It
analyzed 80 documents before the deadline. The internal extraction event table
contained 87 events, while the Generic Task exposed only `task.created`.
External API monitoring therefore received no document progress.

## Correction

Version 0.27.0 removes the aggregate wall-clock deadline. The QueueItem lease
and worker heartbeat represent liveness. The per-document Ollama HTTP deadline
continues to bound a stalled model request.

Every `KnowledgeExtractionTaskDocument` now commits its own terminal checkpoint
and publishes a Generic Task `task.progress` event. Scope, manifest and
aggregation transitions use the same public stream. Running API responses
return persisted state counts, progress rate and the last progress timestamp.

## Production validation

The real organization `0276 滋賀大学` was submitted again as Extraction
`5cd11502-565f-4ec6-949a-539112cbfb7b`, Generic Task
`0366ac6e-aacf-4c1c-8875-d73705bd3516`. It resolved the same 452-document
scope. While active, the API monitor showed version 0.27.0, an executing task,
hundreds of actions and continuously increasing global and task sequences.

It completed at 06:35:44 JST after approximately 5 minutes 29 seconds. The
terminal extraction state was `review_required` with `EXTRACTION_PARTIAL`:
452 total documents, 134 ready, 128 analyzed, 285 failed, 39 excluded and a
coverage rate of 0.309927. The Generic Task completed with 458 public events.
Their composition was one `task.created`, one `task.started`, 455
`task.progress` and one `task.completed`. The progress events contained 452
document terminal reports: 128 extracted, 285 failed and 39 excluded.

## Frontend replay correction

Production completion validation found a separate monitor issue. During a
large SSE history replay, each event for a Task absent from the initial list
could call `refreshAudit()` concurrently. The list request now has a
single-flight Promise guard. A regression assertion proves that consecutive
unknown Task events share one additional list request. After deployment, a
browser reload restored the completed 458-action card, and the Console had zero
warnings or errors.
