# Large source collection investigation

Release: 0.12.0

## Symptom

The `UPDS顧客別情報` network share remained at “collecting resources” for an
extended period and showed no new events.

## Runtime evidence

At 16:28 Japan time the ingestion remained `running` with its last event at
`knowledge.collection.started`. Gateway CPU time continued increasing. The SMB
connection to the target share remained healthy and its open-handle count
increased from 981 to 1022 during observation.

The evidence showed active traversal with insufficient progress feedback.

The same ingestion recorded two `knowledge.ingestion.started` and two
`knowledge.collection.started` events. The API returned an existing active
ingestion and then scheduled `ingest()` again, which allowed concurrent
collection of one source.

## Source evidence

The previous connector built and sorted one complete `root.rglob("*")` result
before the collection-completed event. Network-share enumeration had no
directory progress callback. The Git and SVN command timeout did not apply to
UNC directory traversal.

## Implemented correction

* Replace recursive whole-tree discovery with a breadth-first directory queue.
* Open, list and close one directory before advancing.
* Do not follow directory symlinks.
* Skip excluded dependency, cache and version-control directories before they
  enter the queue.
* Emit start and completion progress facts for every directory.
* Show relative directory, scanned and pending directory counts, and file
  discovery and processing counts.
* Reuse an active ingestion without scheduling it again.
* Require `queued` state inside `ingest()` as a second execution gate.
* Automatically connect the Knowledge page to active scheduled ingestion SSE.
* Retain only the latest 200 events in browser memory while counting the full
  received stream separately.
* Treat an encrypted or unreadable PDF as one rejected file and continue the
  source traversal.

## Remaining boundary

Document contents remain in the current in-memory collection snapshot until
cleaning and chunking complete. This release removes whole-tree directory
enumeration and duplicate collectors. Streaming document persistence can be a
separate future optimization for sources whose extracted text exceeds the
configured host memory budget.
