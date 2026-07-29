# Validation commands

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

```powershell
$env:AGENT_GATEWAY_TEST_POSTGRES_URL = "<temporary PostgreSQL URL>"
$env:AGENT_GATEWAY_TEST_MIGRATION_POSTGRES_URL = `
  "<temporary migration PostgreSQL URL>"
.\.venv\Scripts\python.exe -m pytest `
  tests/test_pgvector_integration.py -vv -s -o addopts=
```

```powershell
cd frontend
pnpm test -- --run
pnpm build
```

```powershell
Invoke-Pester -Script scripts/tests/LocalCodexGateway.Tests.ps1
docker compose config --quiet
docker compose build gateway
```

```powershell
Invoke-RestMethod http://127.0.0.1:8015/health/ready
```

The 8015 validation used a temporary PostgreSQL database and container. Both
were removed after verification.
