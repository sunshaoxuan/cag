# Commands

## Verification

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest

cd D:\workspace\cag
D:\nginx\runtime\node\pnpm.cmd --dir frontend test -- --run
D:\nginx\runtime\node\pnpm.cmd --dir frontend exec tsc --noEmit
D:\nginx\runtime\node\pnpm.cmd --dir frontend build
docker compose config --quiet
git diff --check
```

## Formal configuration and migration

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.knowledge.artifact_keyring_cli init
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current

cd ..
.\scripts\manage-local-codex-gateway-task.ps1 -Action stop -Port 8000
.\scripts\manage-local-codex-gateway-task.ps1 -Action start -Port 8000
```

The first complete-suite attempts used execution timeouts of 5 and 124 seconds
and were terminated before a test result. A later complete run found an old
health version assertion and 84.93% coverage. Both were repaired and the full
suite restarted from the beginning. One migration invocation from the repository
root could not find `backend/alembic.ini`; the same test passed from `backend`.
One final-count command from the repository root did not load
`backend/.env.local`; it made no database change and was repeated successfully
from `backend`.
