# Commands and observed results

All commands ran on 2026-08-05 in `D:\workspace\cag`.

## Static and repository checks

```text
git status --short --branch
## master...origin/master

git diff --check
exit code 0

rg direct OpenAI call patterns in backend/app, scripts and backend/pyproject.toml
NO_DIRECT_OPENAI_CALLS_IN_CAG_RUNTIME
```

## Automated verification

```text
backend: .\.venv\Scripts\python.exe -m pytest
123 passed, 2 skipped, coverage 85.97%

frontend: bundled pnpm test
3 test files passed, 17 tests passed

frontend: bundled pnpm build
vite production build passed

PowerShell: Invoke-Pester -Path scripts/tests/LocalCodexGateway.Tests.ps1
10 passed, 0 failed
```

## Live service verification

```text
GET http://127.0.0.1:8000/health/ready
{
  "status": "ready",
  "version": "0.22.7",
  "queue_running": true,
  "redis_connected": true,
  "backend": "postgresql",
  "native_vector_search": true,
  "pgvector_version": "0.8.2"
}

Get-NetTCPConnection -LocalPort 8000 -State Listen
LocalAddress 0.0.0.0, LocalPort 8000

GET http://127.0.0.1:5173
HTTP 200, title One Agent Gateway
```

## Real API Key Agent smoke

```text
GET /api/v1/tasks/8e752931-0ebf-4438-9302-d53fb0ffaf67
status: completed
summary: API_KEY_RUNTIME_SMOKE_OK
changes: []

Task SSE event runtime.connected
provider: local-codex-app-server
authentication: apiKey
```

The post-push release smoke used task
`835b1672-bae0-41dd-8d62-5a759ef474d2` and returned
`API_KEY_RELEASE_SMOKE_OK`. Its durable `runtime.connected` event again
reported `local-codex-app-server` with `authentication=apiKey`, and the task
completed without file changes.
