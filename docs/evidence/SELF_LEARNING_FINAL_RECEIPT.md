# Self learning final receipt

## Release

Version 0.7.0.

## Implemented evidence

* Durable capability, evaluation, promotion, rollback, Gardener and standards
  control records.
* Repeated task learning signal and proposed Skill creation.
* Fixed benchmark gates with 20 replays and two project contexts.
* Ten successful shadow runs and five successful canary runs.
* External installation and rollback receipts.
* Sensitive content and incomplete schema rejection.
* Gateway registry boundary with no direct formal Skill overwrite.

## Verification

* Backend: 57 passed.
* Backend coverage: 88.30 percent.
* Frontend: 6 passed.
* Frontend production build: passed.
* Real Ollama first ingestion: one file and one 1024-dimensional vector written.
* Real Ollama unchanged repeat: one unchanged file, zero chunks written and one
  vector reused.
* Legacy SQLite baseline: detected at 0.4.0 and upgraded in place to
  `20260727_0007`.

## Rollback

Downgrade the database from `20260727_0007` to `20260727_0006a`, restore
version 0.6.0 application images, and retain external receipts as audit
evidence.
