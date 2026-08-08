# Command log

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/queue/status
Invoke-RestMethod http://127.0.0.1:8000/api/v1/tasks/1294cbdc-5539-4cf7-9d8c-f85cafd92525
docker exec cag-postgres-1 psql -U agent_gateway -d agent_gateway
docker logs --since 15m ollama
.\.venv\Scripts\python.exe -m pytest
Invoke-Pester -Path .\scripts\tests\LocalCodexGateway.Tests.ps1
D:\nginx\runtime\node\pnpm.cmd test
D:\nginx\runtime\node\pnpm.cmd build
git diff --check
git status --short
Get-CimInstance Win32_Process
Get-NetTCPConnection -State Listen -LocalPort 8000
```

Browser acceptance used the in-app browser for CAG and attempted both the in-app browser and Edge for OneOps.

Final runtime verification on 2026-08-09 confirmed CAG `0.26.0`, one configured
`extraction` worker, target QueueItem `completed`, one active worker process tree
and one API listener on port 8000.
