# Verification commands

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest

cd D:\workspace\cag\frontend
pnpm test
pnpm run build

cd D:\workspace\cag
docker compose config --quiet
docker compose build gateway frontend
docker compose run --rm gateway alembic upgrade head
docker compose run --rm gateway alembic downgrade 20260728_0010
docker compose run --rm gateway alembic upgrade head

docker run --rm cag-gateway:latest python -c "from app.knowledge.code_intelligence import analyze_code; ..."
```

The desktop bundled Node runtime supplied `pnpm` because the user PowerShell
PATH did not contain Node.js.
