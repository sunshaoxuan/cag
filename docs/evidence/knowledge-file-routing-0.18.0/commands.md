# Verification commands

Backend full suite:

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest
```

Frontend component and production build:

```powershell
cd D:\workspace\cag\frontend
pnpm test -- --run
pnpm run build
```

Isolated PostgreSQL migration and native vector search:

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m pytest `
  tests\test_pgvector_integration.py::test_pgvector_storage_and_native_search `
  --no-cov -q
```

Repository gates:

```powershell
git diff --check
git status --short
```

Browser verification used isolated loopback ports 8018 and 5180. The production
listeners on 8000 and 5173 were not restarted.
