# Command log

```powershell
.\.venv\Scripts\python.exe -m pytest
D:\nginx\runtime\node\pnpm.cmd test
D:\nginx\runtime\node\pnpm.cmd build
.\scripts\manage-local-codex-gateway-task.ps1 -Action stop
.\scripts\manage-local-codex-gateway-task.ps1 -Action start
Invoke-RestMethod http://127.0.0.1:8000/health/ready
Invoke-RestMethod http://127.0.0.1:8000/api/v1/queue/status
Invoke-RestMethod http://127.0.0.1:8000/api/v1/knowledge/extractions/customer-ledger/5cd11502-565f-4ec6-949a-539112cbfb7b
Invoke-RestMethod http://127.0.0.1:8000/api/v1/audit/tasks/0366ac6e-aacf-4c1c-8875-d73705bd3516
Invoke-WebRequest 'http://127.0.0.1:8000/api/v1/audit/events?follow=false&task_id=0366ac6e-aacf-4c1c-8875-d73705bd3516'
docker compose up -d --no-deps --build frontend
git diff --check
git status --short
```

Browser acceptance used the CAG API monitor at
`http://127.0.0.1:5173/audit` and inspected the active state, completed-state
reload, Console and screenshots.
