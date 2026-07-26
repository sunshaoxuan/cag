# Evidence index

Version: 0.1.0

| Evidence | Purpose | Result |
|---|---|---|
| `docs/Agent Gateway 建设任务.docx` | Authoritative feature specification | Parsed structurally |
| `docs/architecture.md` | System and Phase 1 design | Reviewed against first-round scope |
| `docs/adr/0001-local-codex-runtime.md` | Runtime and authentication decision | Accepted |
| `backend/tests` | Unit, API, event, failure and migration evidence | 14 passed |
| Pytest coverage report | Executed source coverage | 96.75 percent |
| `docker compose config --quiet` | Compose syntax and interpolation | Passed |
| `docker compose up -d --build` | Image build and service startup | Passed |
| `docker compose ps` | Runtime service health | Three healthy services |
| PostgreSQL `alembic_version` | Applied schema revision | `20260727_0001` |
| PostgreSQL table query | Physical schema | Five expected tables |
| Live `POST /api/v1/tasks` | Task admission | HTTP 202 |
| Live task SSE | Ordered runtime events | Sequences 1 through 6 |
| Local Codex `login status` | Authentication boundary | Logged in using ChatGPT |
| Local Codex help output | Installed capability | app-server and exec JSON available |
