# Validation commands

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest tests/test_knowledge.py -q --no-cov
.\.venv\Scripts\python.exe -m pytest tests/test_migrations.py -q --no-cov
.\.venv\Scripts\python.exe -m pytest

cd D:\workspace\cag\frontend
pnpm test -- --run
pnpm run build

cd D:\workspace\cag
docker compose config
git diff --check
git status --short
```

Deployment and live acceptance also run:

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\alembic.exe upgrade head

cd D:\workspace\cag
.\scripts\manage-local-codex-gateway-task.ps1 start
docker compose up -d --build frontend
```
