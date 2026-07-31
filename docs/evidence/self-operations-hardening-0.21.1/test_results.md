# Version 0.21.1 test results

| Gate | Result |
|---|---|
| Backend focused operations and health | 7 passed |
| Backend full suite | 114 passed, 2 skipped |
| Backend coverage | 85.63% |
| Frontend unit suite | 14 passed |
| Frontend production build | passed |
| Invalid administrator token | HTTP 401 |
| Authenticated identity audit | passed |
| Runtime delta persistence | zero durable delta events |
| Browser authenticated rejection | passed |
| Browser session credential retention | passed |
| Browser console | 0 warnings, 0 errors |

One focused multi-test run observed an existing asynchronous wake timing case
that remained `detected` for 15 seconds after a failed manual evaluation. The
same test passed alone, the complete operations file passed on rerun and the
full 116-item collection completed with 114 passes and the two configured
PostgreSQL skips. The transient result is retained here for traceability.
