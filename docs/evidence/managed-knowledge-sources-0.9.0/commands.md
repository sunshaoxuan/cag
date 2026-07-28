# Commands

Credential values and credential contents are excluded.

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git --version
svn --version --quiet
svnadmin --version --quiet

cd backend
.\.venv\Scripts\python.exe -m compileall app
.\.venv\Scripts\python.exe -m pytest tests/test_knowledge.py --no-cov -q
.\.venv\Scripts\python.exe -m pytest tests/test_migrations.py --no-cov -q
.\.venv\Scripts\python.exe -m pytest

cd ..\frontend
pnpm test
pnpm run build

docker compose config
git diff --check
git status --short
```

Browser validation used a separate loopback Gateway on port 8010 and a static
production frontend on port 5174. It did not interrupt the managed 8000 and
5173 services used by the independent 0.8.2 task.
