# Test results

| Check | Result |
|---|---|
| Backend full suite | 83 passed, 2 external integration tests skipped |
| Backend coverage | 85.32 percent, required threshold reached |
| Real PostgreSQL pgvector integration | 2 passed |
| SQLite to pgvector complete test migration | Passed with physical-ID, row, vector and dimension verification |
| Frontend component suite | 11 passed |
| Frontend TypeScript and production build | Passed |
| PowerShell script suite | 7 passed |
| Compose configuration | Passed |
| Gateway container build | Passed |
| Temporary 0.15.0 readiness | PostgreSQL, native vector search true, pgvector 0.8.2 |
| Browser DOM and screenshot | Passed |
| Browser console capture | Unavailable on the selected control surface |
| Live source migration preflight | Blocked as required, integrity ok, active ingestion preserved |

The Python coverage C tracer was blocked by the local application-control
policy. Coverage used the Python tracer and still reached the configured gate.
