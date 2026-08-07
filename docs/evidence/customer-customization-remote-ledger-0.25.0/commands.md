# Verification commands

Run from `D:\workspace\cag\backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run from `D:\workspace\cag`:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health/ready
Invoke-RestMethod http://127.0.0.1:8000/api/v1/queue/status
Invoke-RestMethod http://127.0.0.1:8000/api/v1/knowledge/extractions/customer-ledger/fc2519ed-509f-49de-8c49-625e330412d3
rg -n "0408|筑波大学|筑波大" backend/app frontend/src scripts
git diff --check
git status --short
```

No command in this record contains credentials.
