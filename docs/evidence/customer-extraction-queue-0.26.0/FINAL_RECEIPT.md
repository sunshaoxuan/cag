# CAG 0.26.0 final receipt

## Delivered

Customer-facing ledger extraction now has an independent durable queue and worker capacity. Full-source ingestion cannot occupy that capacity. Ollama document calls have an HTTP-enforced deadline, bounded context and bounded evidence. Observed directory aliases select the correct field contract. Successful retries have consistent state. Windows restarts stop owned process trees.

## Verification

* Backend full suite: 162 passed, 3 skipped, coverage 85.40 percent.
* Frontend: 17 passed and production build passed.
* PowerShell runtime tests: 10 passed.
* Production target action completed with 85 candidates.
* CAG browser page and Console passed.
* OneOps browser acceptance: `evidence_missing` because both available browser surfaces were blocked before authentication.
* Final restart check: one API listener, one current worker process tree, one idle extraction worker and zero queued extraction items.

## Rollback

Restore the previous Git revision and VERSION 0.25.0. Stop the scheduled Gateway, move queued extraction items to `knowledge`, restart the prior runtime and verify worker leases. Do not delete completed extraction results, candidates or citations.

## Release provenance

Implementation commit: `5f87e8c` (`fix: isolate customer extraction queue`).
The release tag is `v0.26.0`; remote equality is checked after the evidence
receipt commit and tag are pushed.
