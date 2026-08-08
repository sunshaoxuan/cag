# Final acceptance checklist

| Original intent | Result | Evidence |
|---|---|---|
| OneOps customer extraction does not wait behind full ingestion | Passed | Dedicated extraction queue and production completion |
| Existing queued action is recovered | Passed | Target Task and QueueItem completed |
| Extraction remains durable across restart | Passed | Five claims resumed persisted document checkpoints |
| Model calls have bounded request time | Passed | HTTP timeout contract test and production 15 second failures |
| Prompt remains inside governed bounds | Passed | Relevant schema and 4,000 character evidence test; no final-window truncation |
| Directory spelling variants select correct fields | Passed | NFKC alias test and production throughput |
| Retry state is internally consistent | Passed | Regression test and production stale count zero |
| Restart leaves no old worker process | Passed | Owned process-tree cleanup test and controlled runtime restart |
| Required code, docs, version and changelog are updated | Passed | Repository diff |
| Backend, frontend and runtime tests pass | Passed | `test_results.md` |
| Changed CAG UI passes Browser, Console and screenshot checks | Passed | `cag-extraction-queue-status.png`, zero Console issues |

## Additional observation

The OneOps UI was not changed by this release. An additional attempt to capture
the completed card was blocked by Windows domain authentication in the in-app
browser and Edge client policy. The exact Task behind that card was verified as
`completed` through the production API and QueueItem foreign-key chain.
