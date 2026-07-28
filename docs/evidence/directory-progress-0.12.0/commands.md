# Validation commands

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest tests/test_knowledge.py -q --no-cov
.\.venv\Scripts\python.exe -m pytest

cd D:\workspace\cag\frontend
pnpm test -- --run
pnpm run build

cd D:\workspace\cag
docker compose config --quiet
git diff --check
git status --short
```

Live acceptance:

```powershell
cd D:\workspace\cag
.\scripts\manage-local-codex-gateway-task.ps1 stop
.\scripts\manage-local-codex-gateway-task.ps1 start
docker compose up -d --no-deps --build frontend
```

The live check reads the active ingestion through the API with `follow=false`,
confirms `knowledge.collection.progress` events, samples SMB activity and
checks the Knowledge page, browser console and screenshot.
