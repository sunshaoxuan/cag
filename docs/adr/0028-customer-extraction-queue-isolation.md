# ADR 0028: Customer extraction queue isolation

## Status

Accepted for version 0.26.0.

## Context

Full-source knowledge ingestion and scoped customer ledger extraction used the
same `knowledge` queue. The production source contained 742,066 chunks. Its
single ingestion lease remained healthy while embedding checkpoints advanced,
so the only knowledge worker could not claim a higher-priority OneOps
extraction. Queue priority orders the next claim and does not preempt a running
lease. The accepted extraction remained queued with zero attempts.

Customer-facing extraction has a bounded response expectation and reads the
last active knowledge generation. It must not wait for an unrelated full-source
refresh to finish.

## Decision

1. Route every `customer_knowledge_extraction` job to a durable `extraction`
   queue.
2. Run at least one extraction worker independently from the `knowledge`
   ingestion worker pool.
3. Keep PostgreSQL as queue authority and Redis as wake-up transport.
4. Preserve the physical Task, KnowledgeExtractionTask and QueueItem links.
5. Restore a missing QueueItem for a `knowledge_extraction` Task to the
   extraction queue with priority 120 during durable bootstrap.
6. Publish extraction wake-ups for creation, extraction cancellation and the
   generic queue cancellation endpoint.
7. Report extraction capacity, queued work and leased work through the queue
   status API and API documentation UI.
8. Apply the per-document deadline to the Ollama HTTP request itself and use an
   8192-token generation context. ADR 0029 replaces the aggregate wall-clock
   deadline with lease-based liveness and durable document progress.
9. Normalize directory taxonomy with NFKC and map the observed
   `2.カスタイズ情報` alias to customization-only extraction so path spelling
   variants cannot expand a document prompt to every ledger field.
10. Send only schemas referenced by the selected document fields. Bound model
    evidence to eight ordered chunks and 4,000 total characters, with 2,000
    characters from one chunk.
11. A successful document retry clears its prior failure code before committing
    the analyzed checkpoint.
12. The Windows launcher stops each owned API and worker process tree,
    including virtual-environment base Python children, before disposal.

## Consequences

A full-source ingestion can occupy its only worker for many hours while a
customer extraction is claimed by its own worker. Extraction and ingestion may
still use shared model infrastructure, whose own bounded request scheduling
remains observable through extraction stages and per-document deadlines. Adding extraction
capacity uses one additional worker loop and database heartbeat.

## Acceptance

1. A blocked knowledge ingestion remains leased while a newly accepted
   customer extraction reaches a terminal state through the extraction worker.
2. The extraction QueueItem records queue name `extraction`, one attempt and a
   terminal state.
3. Queue status reports independent extraction worker capacity.
4. Bootstrap reconstructs a missing extraction QueueItem with the correct job
   type, queue and priority.
5. An Ollama request receives the configured document timeout and generation
   context, then records a bounded document failure when the model exceeds it.
6. Formal and observed customization directory spellings select only the
   customization field contract.
7. A prompt with more than eight large chunks excludes excess chunks from both
   evidence and the authoritative citation enum, and remains inside the
   document evidence budget.
8. The production OneOps action is moved to the extraction queue, claimed and
   reaches a terminal state while the full ingestion continues.

## Rollback

Restore version 0.25.0 and its queue configuration. Before rollback, stop the
worker and move any queued extraction items back to the knowledge queue so the
older worker can recognize them. Restart the API and worker, then verify queue
heartbeats and Task status.
