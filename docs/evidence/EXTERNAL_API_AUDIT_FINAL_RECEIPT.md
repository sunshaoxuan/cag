# External API audit release receipt

## Release

* Version: 0.8.0
* Date: 2026-07-27
* Scope: external task API traceability and global action audit

## Implemented behavior

* External callers submit tasks without using the CAG website.
* Every accepted task returns a Trace ID, task event URL and audit URL.
* Client ID, request ID, source, request hash and idempotency behavior are durable.
* Every TaskEvent receives a Gateway global audit sequence.
* A resumable global SSE projects all task actions as `audit.event`.
* Audit APIs query calls and individual traces.
* The React task page identifies itself as a test console.
* The React audit page monitors external and test-console calls.

## Verification

| Check | Result |
|---|---|
| Backend pytest | 62 passed, 88.69 percent coverage |
| Frontend tests | 8 passed |
| TypeScript and Vite build | Passed |
| Alembic upgrade and downgrade | Dedicated upgrade, downgrade and re-upgrade passed; live database upgraded to `20260727_0008` |
| Docker Compose validation | Passed |
| Real local external HTTP submission | Completed through ChatGPT-authenticated Codex |
| Global audit SSE and resume | Passed in automated tests |
| Browser audit monitor | Passed with external Trace `5c7fe35f-5f5a-4d07-a6d1-ad2b99f2cbed` |
| Browser console | Passed, zero warnings and errors |

The real external call emitted 27 durable events from `task.created` through
`task.completed`, covering global sequences 5458 through 5484. Replaying the
same Idempotency Key returned the same Trace ID without reexecution.

The browser monitor replayed all 5,484 persisted audit events and displayed the
operator-selected latest 100 rows. The backend count and visible-row count were
shown separately.

## Security boundary

The current local runner binds to `127.0.0.1`. Publishing across machines
requires Gateway caller authentication, project authorization, HTTPS and rate
limiting. No OpenAI API Key is required or stored.

## Rollback

Downgrade Alembic from `20260727_0008` to `20260727_0007`, revert the 0.8.0
release commit and redeploy the 0.7.2 frontend and Gateway.
