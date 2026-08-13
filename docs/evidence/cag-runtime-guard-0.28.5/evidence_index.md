# Evidence index

| Evidence | Purpose |
|---|---|
| `scripts/manage-local-codex-gateway-task.ps1` | Three-trigger scheduled-task registration and duplicate-start policy |
| `scripts/supervise-local-codex-gateway.ps1` | Live, Ready, process identity and restart behavior |
| `scripts/tests/LocalCodexGateway.Tests.ps1` | Parser, trigger, health and runtime task assertions |
| `workspaces/.gateway/logs/gateway-supervisor.log` | Persistent local start, health and restart timeline |
| `browser-home.png` | Browser-rendered 0.28.5 management UI acceptance |
| `/health/ready` runtime response | Version, queue, Redis, PostgreSQL and pgvector evidence |
