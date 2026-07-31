# Final receipt

Version: 0.22.0

Status: deployed and verified

## Outcome

The self-operations issue center now stores a reviewer-facing decision brief,
explicit implementation route and fail-closed Review state. Complete evidence
remains available separately.

`OI-6B26534BF5` was migrated, re-planned and independently reviewed. Its current
route is `mixed`, its plan requires revision, and eight blocker records are
visible to the administrator.

## Verification

* backend full regression passed;
* frontend tests and production build passed;
* SQLite and PostgreSQL migrations passed;
* PostgreSQL downgrade and re-upgrade passed;
* production listener, readiness, migration and supervisor passed;
* blocked production approval returned HTTP 409;
* browser structure, interaction, console and screenshots passed.

## Rollback

Restore the pre-release PostgreSQL backup when data rollback is required, revert
the release commits, downgrade Alembic to `20260731_0017`, rebuild the frontend
container and restart the managed Gateway task. Preserve a separate export of
0.22.0 issue records when the new decision history must remain auditable.
