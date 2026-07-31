# Version 0.21.0 validation commands

## Backend

```powershell
Set-Location D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest
```

## PostgreSQL and pgvector

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest tests\test_pgvector_integration.py -vv --no-cov
```

The pgvector storage test and the completed SQLite migration test used
separate temporary PostgreSQL databases. Both databases were removed after
validation.

## Supervisor

```powershell
Invoke-Pester .\scripts\tests\LocalCodexGateway.Tests.ps1
```

## Frontend

```powershell
pnpm test
pnpm build
```

## Browser

The backend and Vite UI were started on `127.0.0.1:8011` and
`127.0.0.1:5175`. Browser validation covered the issue list, dashboard,
approval controls, plan and Review artifacts, timeline, responsive header and
console log.

## Release

```powershell
git diff --check
git status --short
.\scripts\manage-local-codex-gateway-task.ps1 start
```
