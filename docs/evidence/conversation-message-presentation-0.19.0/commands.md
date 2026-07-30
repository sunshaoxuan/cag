# Commands

## Dependency and frontend validation

```powershell
pnpm add react-markdown remark-gfm
pnpm test
pnpm build
pnpm audit --prod
```

## Backend regression

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

## Browser acceptance

An isolated Fake Runtime backend listened on `127.0.0.1:18019`. A Vite
frontend listened on `127.0.0.1:15173` and proxied `/api` to that backend.
The isolated queue used one interactive worker and one knowledge worker.
Production ports `8000` and `5173` were not modified.

After acceptance, both listeners, both SQLite files, cloned workspaces, logs
and temporary launch configuration were removed.
