# Verification commands

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest
```

```powershell
cd D:\workspace\cag\frontend
pnpm test
pnpm build
```

```powershell
cd D:\workspace\cag
docker build -f frontend/Dockerfile -t cag-frontend:0.16.0 .
docker run --rm -d --name cag-frontend-0160-validation `
  -p 127.0.0.1:5174:80 `
  -e CAG_GATEWAY_UPSTREAM=host.docker.internal:8000 `
  cag-frontend:0.16.0
```

```powershell
git diff --check
git status --short
```
