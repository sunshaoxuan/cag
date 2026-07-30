# Version 0.17.1 validation commands

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest
```

```powershell
cd D:\workspace\cag\frontend
pnpm test -- --run
pnpm build
```

```powershell
cd D:\workspace\cag
Invoke-Pester -Path scripts/tests/LocalCodexGateway.Tests.ps1 -PassThru
.\scripts\manage-local-codex-gateway-task.ps1 start
.\scripts\manage-local-codex-gateway-task.ps1 status
docker compose config --quiet
```

Runtime acceptance also queried `/health/ready`, `/api/v1/queue/status`,
PostgreSQL vector counts, the migration receipt, the listener owner, Task
Scheduler settings and the supervisor log.
