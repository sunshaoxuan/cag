# Commands

1. Inspect listeners, processes, Compose services, scheduled tasks and services.
2. Inspect scheduled-task actions, results and supervisor logs.
3. Validate PostgreSQL inside the container and from the host Python runtime.
4. Restart only CAG PostgreSQL and Redis containers to restore host forwarding.
5. Register and start `CAG Local Codex Gateway` through `manage-local-codex-gateway-task.ps1`.
6. Terminate only the verified Uvicorn port 8000 process and wait for automatic Ready recovery.
7. Run backend pytest, frontend tests and build, and Pester supervisor tests.
8. Restart the formal managed runtime and inspect Ready version 0.28.5.
9. Inspect browser DOM, Console and full-page screenshot at `http://127.0.0.1:5173/`.
10. Run `git diff --check`, commit on master, push to `origin/master`, and compare refs.
11. Inspect the OneOps-configured primary port 8001 and fallback port 8002.
12. Re-register both formal scheduled tasks through the 0.28.5 manager.
13. Call `/api/v1/projects` through each LAN endpoint.
14. Execute OneOps `testAgentGatewayConnection()` against both configured endpoints.
15. Remove only the stopped duplicate `Backup` and `Standby` scheduled tasks.
