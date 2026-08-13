# Evidence index

| Evidence | Purpose |
|---|---|
| `scripts/manage-local-codex-gateway-task.ps1` | Three-trigger scheduled-task registration and duplicate-start policy |
| `scripts/supervise-local-codex-gateway.ps1` | Live, Ready, process identity and restart behavior |
| `scripts/tests/LocalCodexGateway.Tests.ps1` | Parser, trigger, health and runtime task assertions |
| `workspaces/.gateway/logs/gateway-supervisor.log` | Persistent local start, health and restart timeline |
| `browser-home.png` | Browser-rendered 0.28.5 management UI acceptance |
| `/health/ready` runtime response | Version, queue, Redis, PostgreSQL and pgvector evidence |
| OneOps `gateway/agent-gateway-settings.mjs` production function | Actual `/projects` connection-test contract and primary/fallback results |
| Scheduled tasks for ports 8000, 8001 and 8002 | Formal OneOps primary and fallback continuity configuration |
