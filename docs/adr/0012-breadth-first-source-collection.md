# ADR 0012: Breadth-first source collection

Status: Accepted

Accepted for version 0.12.0.

## Context

A network share containing many directories remained at
`knowledge.collection.started` for an extended period. Runtime inspection
showed an active SMB connection and increasing file activity. The collector
used one recursive `Path.rglob("*")` expression and emitted its next event only
after discovering and sorting the complete tree.

The ingest API also returned an existing active ingestion and scheduled its
`ingest()` coroutine again. One ingestion therefore could have multiple
collectors traversing the same source.

## Decision

Folder-backed sources use a breadth-first queue:

1. Dequeue one directory.
2. Open and list that directory only.
3. Queue allowed child directories in stable name order.
4. Process supported files from the current directory.
5. Close the directory handle and advance to the next item.

The collector emits a durable progress fact when each directory starts and
finishes. The fact includes a relative directory, queue counts and file counts.

`create_ingestion()` returns whether the ingestion was newly created. API and
scheduler callers start execution only for a new row. `ingest()` independently
requires the queued state before execution.

## Consequences

* Shallow directories become observable before deep descendants.
* A large source produces continuous progress without requiring file-level
  event volume.
* Only one directory enumeration handle belongs to each collector.
* Repeated ingest calls attach to the same SSE sequence.
* Encrypted or unreadable PDFs count as rejected files and do not terminate the
  remaining source traversal.
* Collected document text remains in the existing in-memory snapshot until the
  later chunking phase. A future streaming-index design can reduce that memory
  boundary independently.

## Verification

* Connector test proves breadth-first completion order and final counts.
* API test proves one start and one collection execution for repeated calls.
* SSE and frontend tests prove directory progress projection.
* Encrypted-PDF isolation test proves one unreadable file does not stop the
  remaining collection.
* Live Windows network-share acceptance verifies increasing directory and file
  counts.

## Rollback

Deploy version 0.11.0. No database downgrade is required because this decision
adds no schema objects.
