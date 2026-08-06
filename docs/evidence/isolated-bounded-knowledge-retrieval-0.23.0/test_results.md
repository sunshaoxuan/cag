# Test results

| Acceptance item | Result | Evidence |
| --- | --- | --- |
| Complete backend | passed | 134 passed, 3 skipped, 85.25 percent coverage |
| PostgreSQL pgvector storage and native search | passed | explicit fresh PostgreSQL test database |
| API and worker process isolation | passed | explicit PostgreSQL dual process test |
| SQLite cutover at current head | passed | explicit fresh PostgreSQL migration database |
| Queue cancellation and completion ordering | passed | both timestamp orders covered |
| Scheduled ingestion cancellation | passed | next sync advanced and lease released |
| Customer exact Code and name | passed | 165.3 ms and 115.2 ms production results |
| Customer structured extraction | passed | Task `a109cff6-8c7f-467d-b8d8-da4699693ea2` |
| Running Task cancellation | passed | Task `6206ece4-284f-4d27-89dc-a6469f3f5080`, 1098.4 ms |
| Frontend | passed | 17 component tests and production build |
| PowerShell | passed | 10 Pester tests and parser validation |
| Docker | passed | gateway, worker and frontend images built |
| Browser DOM and Console | passed | `/knowledge`, version 0.23.0, 3 Sources, approved UPDS Generation, zero warnings and errors |
| Browser screenshot | passed | `knowledge-page.png` |

## Test environment note

Project local pytest basetemp runs exposed orphan pytest children after shell
timeouts and severe NTFS contention. The orphan processes were identified by
repository specific command line and terminated. The authoritative complete
suite then passed in pytest's isolated system temporary directory. All project
local one time test directories and dedicated PostgreSQL test databases were
removed before release acceptance.
