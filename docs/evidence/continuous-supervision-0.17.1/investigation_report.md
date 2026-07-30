# One Agent Gateway 0.17.1 continuous supervision investigation

## Initial state

The existing scheduled task was `Ready`, had no triggers, no next run time and
zero restart attempts. Its prior Gateway child had continued independently and
then exited, leaving port 8000 offline.

The legacy SQLite source contained 122 completed and 3 failed knowledge
ingestions. Agent tasks contained 10 completed and 2 failed records. No queued
or running source work remained.

## Implemented control

Task Scheduler now starts the supervisor at system startup and current-user
sign-in. The task has no execution time limit, allows battery operation, starts
when available and retries the supervisor 999 times at one-minute intervals.

The supervisor checks the listener and `/health/ready` every 15 seconds. It
starts the managed launcher when port 8000 is absent. Four consecutive failed
readiness checks restart only the expected Uvicorn Gateway process. An
unexpected port owner is preserved and recorded.

Supervisor logs rotate at 10 MiB and retain five historical files under the
ignored persistent Gateway workspace.

## Migration evidence

The first supervised start performed the guarded SQLite cutover. PostgreSQL
contains 170,807 knowledge chunks and 170,807 vectors. The database receipt
records source SHA256
`8299cc3761c17cc944ecbe5206df1ce91b3374de1f8cc74ec5462369a7185657`
at revision `20260729_0014`.

The consistent snapshot was removed after success. The original
4,051,038,208-byte SQLite database remains available as rollback evidence.

## Runtime evidence

The final Gateway is version 0.17.1 on `0.0.0.0:8000` with PostgreSQL,
pgvector 0.8.2, Redis connected and all queue workers idle. The updated
supervisor entered `gateway.ready` state without changing Gateway PID 11936
during the supervision handover.

A controlled recovery drill then stopped idle Gateway PID 11936. The
supervisor detected the missing listener, started launcher PID 15076 and
restored `0.0.0.0:8000` as Gateway PID 5776 in 45.7 seconds. Supervisor PID
25316 stayed running throughout the drill.

The queue status retained the old process worker heartbeats for the configured
120-second lease window. After that window, the active worker count returned
to the expected three workers, all owned by PID 5776 and all idle.
