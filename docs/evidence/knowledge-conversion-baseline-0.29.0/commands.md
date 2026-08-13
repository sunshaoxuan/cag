# Commands

## Focused verification

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest `
  tests\test_conversion_baseline.py `
  tests\test_migrations.py `
  tests\test_version.py -q --no-cov
```

## Complete backend verification

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

## Frontend verification

```powershell
pnpm test -- --run
pnpm build
```

The bundled Node and pnpm runtime under `D:\nginx\runtime\node` was used.

## Production migration

The existing `backend/.env.local` was loaded into process environment without
printing its values.

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

PostgreSQL advanced from `20260810_0026` through `20260813_0027` to
`20260813_0028`.

## Production dry run

`KnowledgeConversionBaselineService.create_dry_run` ran against Source physical
ID `c4837509-0c4c-4689-bb34-e30a1138da05`. It completed in about 24 seconds and
created run `77ef2f49-8da2-437b-9ecf-a283a43bb326` with 115,668 items.

Pre- and post-run SQL counted Source Entries, Documents, Chunks, embedding
cache, code symbols, code relations and MemoryCandidates. It also verified
manifest aggregation and foreign-key closure.

## Formal runtime deployment

```powershell
.\scripts\manage-local-codex-gateway-task.ps1 -Action stop -Port 8000
.\scripts\manage-local-codex-gateway-task.ps1 -Action start -Port 8000
```

The existing supervised task rebuilt the frontend, ran migrations and started
the API and Worker. It reported ready 0.29.0 on `0.0.0.0:8000`.

## HTTP acceptance

The following formal endpoints were read:

```text
/health/live
/health/ready
/api/v1/knowledge/conversion/format-capabilities
/api/v1/knowledge/conversion-baselines/77ef2f49-8da2-437b-9ecf-a283a43bb326
/api/v1/knowledge/conversion-baselines/77ef2f49-8da2-437b-9ecf-a283a43bb326/items?conversion_action=reclean&limit=3
```

A formal POST dry run against the one-item OCR acceptance Source created run
`ed0fe2b0-28e3-4064-9949-2786af3ad897` and returned one item.
