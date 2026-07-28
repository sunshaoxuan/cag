# Final receipt

Release: 0.12.0

Status: implementation, automated tests and live runtime acceptance complete.
Git publication is recorded by the enclosing repository history.

Delivered:

* Breadth-first directory queue for local folders and network shares
* One-directory-at-a-time enumeration with closed handles
* Durable per-directory progress SSE
* Human-readable directory and file progress in the Knowledge page
* Automatic observation of scheduled collection runs
* Configurable 50, 100 or 200 visible progress events
* Bounded 200-event browser memory projection with a separate received count
* Encrypted-PDF isolation so one protected document cannot terminate a source
* Active-ingestion reuse and queued-state execution guard
* Architecture, API, frontend, security, ADR and evidence documentation

Live acceptance:

* The host Gateway reported version 0.12.0.
* Two immediate ingest API calls returned the same ingestion physical UUID.
* The ingestion recorded one start and one collection-start event.
* The real Windows network share emitted continuous relative-directory
  progress.
* A runtime sample recorded 423 scanned directories, 987 pending directories
  and 787 processed files.
* The scan passed the directory where an encrypted PDF previously terminated
  the ingestion. Rejected files remained isolated and the run stayed active
  without an error.
* The browser automatically followed the scheduled-source ingestion.
* The browser rendered exactly the selected latest 50 events while reporting
  the complete backend event count.
* Browser console warnings and errors were empty.

Rollback:

1. Deploy version 0.11.0.
2. Remove the directory progress event listener from the frontend.
3. Keep existing source and ingestion records.

No database downgrade is required.
