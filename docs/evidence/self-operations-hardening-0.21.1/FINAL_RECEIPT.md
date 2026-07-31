# Version 0.21.1 final receipt

## Scope

Authenticated administrator mutations and bounded self-operations AI event
retention.

## Result

The production AI review findings from 0.21.0 were converted into release
gates, fixed and verified. Read-only issue visibility remains available.
Every state-changing administrator action now requires configured credentials.
Long-term operational issue timelines retain final evidence and exclude
cumulative model token deltas.

Version 0.21.1 is active on the managed production service. The production
operations page passed browser and console inspection. A real network-share
authentication failure has entered the approval queue with AI planning and
independent review completed. It remains unchanged while awaiting an
administrator decision.

## Secret handling

The real administrator token is generated locally, stored only in the ignored
backend environment file and never written to Git, release evidence, prompts
or logs.

## Rollback

Restore the pre-0.21.0 PostgreSQL backup if the database must be rolled back.
For application-only rollback, revert the 0.21.1 hardening commit and restart
the managed task. Removing administrator authentication reopens the production
approval risk and therefore requires an explicit security decision.
