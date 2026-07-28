# Durable knowledge source investigation

## Question

Does the managed knowledge feature provide a long term source system of record
that detects later changes, or does it process only one manually triggered
batch?

## Verified baseline

Before version 0.10.0:

* `KnowledgeSource`, ingestion, document, chunk and vector rows were persistent.
* every ingestion collected a complete current source snapshot
* canonical path and cleaned SHA 256 hash identified unchanged files
* unchanged chunks and vectors were reused
* changed paths were replaced
* removed paths were deleted
* normalized source identity and database uniqueness prevented duplicate source
  registration

The missing control plane was automatic repeated execution. No persisted sync
mode, due time, lease, retry state or scheduler existed. The web page exposed
the latest run and current manual SSE only. It did not expose the existing
source ingestion history.

## Implemented result

Version 0.10.0 adds:

* persisted manual or scheduled policy per source
* sync interval and next due time
* one expiring database lease per claimed source
* startup recovery for interrupted ingestion records
* bounded exponential retry for failures
* last attempt, last content change and consecutive failure state
* manual or scheduled trigger, start time, changed file and removed file counts
* source history API and management page projection
* ten second source status refresh while the Knowledge page is visible

Existing sources migrate to manual mode. This avoids unexpected network or
credential activity during deployment. New registrations made in the web page
default to scheduled synchronization.

## Incremental semantics

Each due run scans the complete source snapshot so deletions are detectable.
Embedding work is incremental. Changed and added files receive new chunks and
vectors. Unchanged paths keep their physical records and vectors. Deleted paths
are removed from document and vector storage. Every run remains in ingestion
history even when it changes no content.
