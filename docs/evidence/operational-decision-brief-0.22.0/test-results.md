# Test results

Date: 2026-07-31

## Backend

Command:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Result:

* 119 collected;
* 117 passed;
* 2 skipped because live pgvector integration is environment-gated;
* process exit code 0;
* reported coverage 85 percent after rounding.

Focused operations and migration command:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests/test_operations.py tests/test_migrations.py -q --no-cov
```

Result: 9 passed.

## Frontend

Commands:

```powershell
pnpm test
pnpm build
```

Results:

* 3 test files passed;
* 14 tests passed;
* TypeScript and Vite production build passed;
* 268 modules transformed.

## PostgreSQL migration

An isolated database named `cag_migration_0220_check` was created in the local
PostgreSQL container. It was upgraded to revision `20260731_0017`, seeded with a
historical CAG-internal waiting-approval issue whose Review contained
`recommendation: revise` and `do_not_approve`, then upgraded to head.

Observed result:

```text
plan_revision_required|revision_required|agent_self_improvement|revise|1|2
```

Downgrade to `20260731_0017` and re-upgrade to head both passed. The isolated
database was removed after verification.
