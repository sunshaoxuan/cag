# Test results

| Check | Result |
|---|---|
| Backend complete suite | PASS, 209 passed, 4 skipped |
| Backend coverage | PASS, 85.07% |
| Artifact focused and S3 contract | PASS |
| Alembic upgrade and downgrade | PASS |
| Version consistency | PASS |
| Frontend components | PASS, 3 files and 23 tests |
| TypeScript | PASS |
| Frontend production build | PASS |
| Compose configuration | PASS |
| Git whitespace check | PASS |
| Formal HTTP API | PASS |
| Production replica disconnect and recovery | PASS |
| Browser DOM | PASS |
| Browser Console | PASS, zero warning and error entries |
| Browser screenshot | PASS |

The four skipped tests are the existing explicitly gated PostgreSQL integration
and process-isolation tests. Formal PostgreSQL migration, HTTP API, database
closure and dual-process runtime were verified separately against production.
