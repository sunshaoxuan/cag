# Version 0.17.0 validation commands

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
docker compose config --quiet
```

The real PostgreSQL integration suite used fresh temporary databases named
`cag_queue_017_test` and `cag_cutover_017_test`, both upgraded through Alembic
revision `20260729_0014`.

```powershell
$env:AGENT_GATEWAY_TEST_POSTGRES_URL = "postgresql+psycopg://agent_gateway:agent_gateway@127.0.0.1:5432/cag_queue_017_test"
$env:AGENT_GATEWAY_TEST_MIGRATION_POSTGRES_URL = "postgresql+psycopg://agent_gateway:agent_gateway@127.0.0.1:5432/cag_cutover_017_test"
$env:AGENT_GATEWAY_REDIS_URL = "redis://127.0.0.1:16379/0"
.\.venv\Scripts\python.exe -m pytest tests/test_pgvector_integration.py -q --no-cov
```

The browser validation used backend port `8017` and frontend port `5174`.
It inspected the API reference, live queue cards, copy interaction, links and
console logs.
