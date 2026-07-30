# Version 0.17.1 test results

| Validation | Result |
|---|---|
| Backend full suite | 107 passed, 2 skipped |
| Backend coverage | 85.43 percent |
| Frontend component tests | 12 passed |
| Frontend production build | Passed |
| PowerShell and supervisor tests | 9 passed |
| Scheduled task state | Running |
| Automatic triggers | 2 |
| Supervisor retry policy | 999 retries, PT1M interval |
| Gateway listener | 0.0.0.0:8000 |
| Gateway readiness | Version 0.17.1, PostgreSQL, pgvector 0.8.2 |
| Redis and queue | Connected, running, three idle workers |
| Migrated vectors | 170,807 |
| Migration receipt | Present at revision 20260729_0014 |
| Browser management page | Version 0.17.1 |
| Browser console | 0 warnings, 0 errors |
| Controlled process-exit recovery | PID 11936 to PID 5776 in 45.7 seconds |

The first supervised database attempt recorded a missing-password startup
failure. The ignored host configuration was then created, and the supervisor
continued into the successful migration and startup.

Runtime review also corrected synchronous launcher invocation so readiness
checks continue while the Gateway is running. The final supervisor logged
`gateway.ready` for the unchanged Gateway PID during handover.

After the handover check, a controlled idle-process exit validated the
asynchronous launcher and missing-listener recovery path end to end.
