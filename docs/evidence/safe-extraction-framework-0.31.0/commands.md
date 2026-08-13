# Command log

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest

cd frontend
pnpm test
pnpm build

docker compose config --quiet
docker compose build gateway worker frontend
docker compose exec -T postgres pg_dump -U agent_gateway -d agent_gateway -Fc
Start-ScheduledTask -TaskName 'CAG Local Codex Gateway'
```

Browser acceptance inspected `/` and `/knowledge`, read the DOM and Console,
and captured a full-page screenshot.
