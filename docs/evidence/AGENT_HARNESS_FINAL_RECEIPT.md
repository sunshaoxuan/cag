# Agent Harness final receipt

Version: 0.6.0

## Result

The governed Harness plane is implemented with parallel read-only investigation, one write-capable Executor, post-execution reviews, structured Artifacts, persistent approvals and CAG-owned unified SSE.

## Verification

* `backend/.venv/Scripts/python.exe -m pytest`: passed.
* frontend tests: passed.
* frontend production build: passed.
* migration revision: `20260727_0006a`.
* balanced Harness browser run: 51 ordered backend events and zero console issues.
* screenshot: `docs/evidence/screenshots/agent-harness-0.6.0.png`.

## Rollback

Downgrade Alembic to `20260727_0005`, restore version 0.5.0 application files and redeploy. Existing Task records keep their knowledge data. Harness tables are removed by the downgrade.
