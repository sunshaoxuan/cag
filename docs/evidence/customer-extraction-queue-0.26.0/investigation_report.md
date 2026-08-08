# CAG 0.26.0 customer extraction queue investigation

## Question

Why did OneOps action `1294cbdc-5539-4cf7-9d8c-f85cafd92525` remain queued, and does the released implementation prevent recurrence?

## Root causes

1. Customer ledger extraction and full-source ingestion shared the single `knowledge` worker.
2. The active ingestion contained 742,066 embedding chunks and held a healthy lease for more than one day. Priority 120 affected only the next claim and could not preempt the running priority 20 ingestion.
3. After queue isolation, document generation exposed an Ollama HTTP cancellation gap. An outer coroutine timeout left the HTTP cleanup waiting for the runner, and Ollama later reported a CUDA runner termination.
4. The production directory spelling `2.カスタイズ情報` did not match the formal taxonomy segment, so each file requested every ledger field.
5. The document prompt contained all object schemas and up to 4,000 characters per chunk. Production prompts reached 10,879 to 16,501 tokens and were truncated.
6. Windows virtual-environment launchers could leave their base Python child alive after the launcher exited, allowing an old worker to renew leases after a restart.

## Implemented correction

* Added a durable `extraction` queue with one dedicated worker.
* Routed creation, cancellation, generic cancellation and bootstrap recovery to the extraction queue.
* Passed the 15 second document deadline to the Ollama HTTP request and set the structured-generation context to 8192 tokens.
* Normalized directory taxonomy with NFKC and recognized the observed customization alias.
* Limited each document prompt to referenced schemas, eight chunks and 4,000 total evidence characters.
* Cleared prior failure codes when a retry completes analysis.
* Recursively stopped owned Windows API and worker process trees.
* Added extraction queue capacity and counts to the API documentation page.

## Production result

The original QueueItem moved from `knowledge` to `extraction`, was claimed by the dedicated worker and completed. The generic Task reached `completed`; the structured extraction reached `review_required` with 85 candidates. Its manifest contained 654 documents, 362 ready documents and 356 analyzed documents. Explicit unavailable, metadata and model failures remained visible, producing coverage 0.624561 and `EXTRACTION_PARTIAL`.

Successful retry rows with a stale failure code were corrected from 36 to zero.

## Browser result

The CAG API page displayed v0.26.0, extraction queue wait zero, one extraction worker and zero Console warnings or errors. The authenticated OneOps page could not be captured in this browser run: the in-app browser remained at Windows domain authentication and Edge returned `ERR_BLOCKED_BY_CLIENT`. The terminal CAG Task and QueueItem were verified directly through the production API and database.

## Remaining limitation

`evidence_missing`: an authenticated OneOps page screenshot for this exact completed action. No OneOps UI code changed in this release.
