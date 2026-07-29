# Test results

| Verification | Result |
|---|---|
| Backend full test suite | 78 passed |
| Backend coverage | 86.71%, required threshold 85% |
| Alembic upgrade, downgrade and re-upgrade | Passed |
| Rejection path, reason and exception persistence | Passed |
| JSON pagination and filtering | Passed |
| UTF-8 BOM CSV export | Passed |
| gzip JSONL archive and SHA 256 receipt | Passed |
| 90-day database-detail retention | Passed |
| 365-day archive retention | Passed |
| Frontend component tests | 11 passed |
| TypeScript production build | Passed |
| Browser product name and version | Passed |
| Browser source lifecycle controls | Passed |
| Browser rejection details and downloads | Passed |
| Browser console | No messages |

Commands:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest

cd ..\frontend
pnpm test -- --run
pnpm build
```

The Python coverage C extension was blocked by the host application-control
policy. Coverage used its Python implementation and passed the configured
threshold.
