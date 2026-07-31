# Version 0.21.1 production deployment

## Deployment

* Application commit: `6a96874073f7bb4dc00a38e56c28ac59182303e5`
* `origin/master` matched the application commit before this evidence update.
* Readiness reported version `0.21.1`, PostgreSQL, pgvector `0.8.2`,
  Redis connected and queue running.
* Alembic revision: `20260731_0017 (head)`
* API listener: `0.0.0.0:8000`
* Management UI: `http://192.168.20.54:5173/operations`, HTTP 200
* The managed supervisor remains configured for long-running service and
  automatic restart.

## Backup

The pre-cutover PostgreSQL backup is:

`D:\workspace\cag\backups\releases\0.21.0-20260731T020718Z\agent_gateway-pre-0.21.0.dump`

* Size: `1753230981` bytes
* SHA-256:
  `45C60F2D8D4C0408059DC01B9E3FFCC66C59C3F4C12DAEC185A8098197F10C52`

## Production security checks

* An invalid administrator token returned HTTP 401.
* An authorized rejection recorded the server-trusted identity
  `release-admin`.
* The local administrator token is stored only in the ignored
  `backend/.env.local` file.
* The browser console reported zero errors on the production operations page.

## Closed bootstrap validation

Issue `OI-E23F303DCC` exercised production intake, local Codex planning,
independent review and the approval gate. The 0.21.1 hardening commit resolved
the two release findings. The validation issue was rejected by
`release-admin`, retained its audit timeline and never created an improvement
branch.

## Real operational issue

Issue `OI-10CE919F81` was created automatically from the failed scheduled
ingestion of `UPDS顧客別情報`.

* Failure: Windows network share authentication, error 86
* Boundary: `credential_or_authorization`, confidence `0.96`
* Severity: high
* State: `waiting_approval`
* Occurrences: 1
* Required input: an administrator or credential owner must validate the
  authorized read-only account and rotate the credential through the protected
  interface.

The planner proposed recovery and a bounded CAG improvement. The independent
review requested revisions for rollback-safe credential rotation, durable
recovery state, source-level single-flight protection, Windows connection
ownership, retrieval availability and secret-surface acceptance tests. No
credential, source configuration, code or branch was changed automatically.

## Verification

* Backend: 114 passed, 2 skipped
* Focused operations tests: 7 passed
* Frontend: 14 passed
* Frontend production build: passed
* Supervisor Pester tests: 9 passed
* Production browser page and console: passed

One combined focused run observed a transient async wake-test process stay.
The standalone test, focused rerun and complete backend suite all passed.
