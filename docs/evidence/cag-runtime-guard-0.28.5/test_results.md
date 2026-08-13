# Test results

| Check | Result |
|---|---|
| Backend full pytest | PASS, 190 passed, 4 skipped, 85.27 percent coverage |
| PowerShell Pester | PASS, 11 passed |
| Frontend Vitest | PASS, 23 passed |
| Frontend production build | PASS, 268 modules transformed |
| Controlled API termination and supervisor recovery | PASS, PID 32548 to PID 31592, Ready in about 45 seconds |
| Formal runtime | PASS, Ready 0.28.5, Redis connected, PostgreSQL, native vector search, pgvector 0.8.2 |
| Scheduled task | PASS, Running, 3 triggers, PT1M repetition, 999 retries, IgnoreNew |
| Browser DOM | PASS, v0.28.5 and primary navigation visible |
| Browser Console | PASS, 0 warnings, 0 errors |
| Browser screenshot | PASS, `browser-home.png` |
| OneOps primary production connection test | PASS, HTTP 200, 1 project, 89 ms |
| OneOps fallback production connection test | PASS, HTTP 200, 1 project, 3 ms |
| CAG ports 8000, 8001 and 8002 | PASS, Ready 0.28.5 on all interfaces, Redis and PostgreSQL ready |
| Formal scheduled-task fleet | PASS, exactly 3 tasks, each Running with 3 triggers and PT1M watchdog |
| Authenticated OneOps DOM, Console and success screenshot | `evidence_missing`, browser authentication session unavailable and Edge control timed out |
| CAG supervisor Pester follow-up | PASS, 11 passed |
| OneOps Agent Gateway settings tests | PASS, 7 passed |
