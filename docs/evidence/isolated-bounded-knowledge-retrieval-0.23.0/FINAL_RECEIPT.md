# Version 0.23.0 final receipt

## Original intent checklist

| Requirement | Artifact | Status |
| --- | --- | --- |
| Isolate knowledge work from API availability | API and worker process roles, host launcher and Compose worker | passed |
| Keep Health, Task, Queue and Cancel responsive | production latency and cancellation probes | passed |
| Prioritize organization Code, official name and alias | exact customer root retrieval | passed |
| Record timeout, candidates, Source, Generation and failed stage | retrieval stage Task events | passed |
| Validate a CAG owned structured customer schema | customer ledger extraction and citation validator | passed |
| Preserve physical IDs and strong references | Task, QueueItem, candidate, Chunk, Source and Generation UUIDs | passed |
| Preserve approved knowledge while cancelling refresh | Source and active Generation production checks | passed |
| Complete release verification | backend, PostgreSQL, frontend, PowerShell, Docker and browser evidence | passed |

## Backup and rollback

Pre release PostgreSQL backup:

`D:\workspace\cag\backups\releases\0.23.0-20260806T040404Z\agent_gateway-pre-0.23.0.dump`

Rollback requires stopping API and worker, restoring the backup when data
rollback is required, reverting the release commit, downgrading Alembic to
`20260805_0020`, rebuilding the frontend and restarting the managed task.

## Release state

Source, migration, tests, build artifacts, production dual-process runtime and
browser acceptance are accepted from the final working tree. The knowledge page
showed version 0.23.0, three Sources, approved UPDS knowledge, zero active runs
after controlled cancellation, and zero Console warnings or errors.
