# Evidence index

Version: 0.2.0

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
| `docs/adr/0003-project-registry-and-task-workspaces.md` | Phase 2 identity and isolation decision | Accepted |
| `backend/tests` | Phase 2 backend behavior | 18 passed, 94.05 percent coverage |
| `frontend/src/App.test.tsx` | Task console component behavior | 3 passed |
| Frontend production build | TypeScript and Vite output | Passed |
| Project API smoke | YAML registry exposed through HTTP | Configured `cag` project returned |
| Live workspace isolation | Two task clones | Distinct workspace IDs |
| Live Phase 2 SSE | Ordered lifecycle | Sequences 1 through 8 |
| `docs/evidence/screenshots/phase2-task-completed.png` | Browser task console | Completed task and report visible |
| Browser console | UI runtime diagnostics | Zero warnings and errors |
| `docs/evidence/phase2_test_results.md` | Phase 2 acceptance record | Passed |
