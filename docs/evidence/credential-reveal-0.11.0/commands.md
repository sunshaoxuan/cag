# Validation commands

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest tests/test_knowledge.py -q --no-cov
.\.venv\Scripts\python.exe -m pytest

cd D:\workspace\cag\frontend
pnpm test -- --run
pnpm run build

cd D:\workspace\cag
docker compose config
git diff --check
git status --short
```

Deployment and live acceptance:

```powershell
cd D:\workspace\cag
.\scripts\manage-local-codex-gateway-task.ps1 stop
.\scripts\manage-local-codex-gateway-task.ps1 start
docker compose up -d --no-deps --build frontend
```

Live credential validation uses a synthetic secret stored through the source
API, checks that generic responses remain secret-free, verifies explicit
reveal headers and exact value recovery, exercises Display and Copy in the
browser, then clears the synthetic Windows Credential Manager entry.
