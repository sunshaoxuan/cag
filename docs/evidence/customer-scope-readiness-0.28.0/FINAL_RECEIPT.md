# CAG 0.28.0 release receipt

## Scope

Customer Scope readiness, historical path governance, Windows Shortcut
flattening, cycle prevention and OneOps processing outcome visibility.

## Current verified state

Implementation, backend tests, frontend tests, production build, host API 0.28.0
deployment, Docker frontend deployment and final production Scope Repair are
verified. Extraction `4cd21c2e-e62f-40cb-8560-4342f29bc794` completed with 470
terminal rows, zero failures and coverage 1.0. Raw hash coverage is 470 of 470.
All analyzed version links and database orphan checks passed.

## Completion gate

CAG commit `dd4581e` and OneOps commit `2f68854` were pushed to their respective
`origin/master` branches. Versions `v0.28.0` and `v0.16.4` were tagged. OneOps
formal title is discoverable. DOM, Console and screenshot communication timed
out twice and remain `evidence_missing`; the static production Bundle, Health,
Gateway, Builder and Portal tests passed.

## Rollback

Restore the prior verified release commit, restart the host Gateway and Worker,
and rebuild only the Docker frontend. Immutable SourceEntry, Document, Chunk,
TaskEvent and extraction records remain available for audit.
