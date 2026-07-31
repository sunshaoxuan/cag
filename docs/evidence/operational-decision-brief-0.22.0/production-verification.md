# Production verification

Date: 2026-07-31

## Deployment

* release commit: `d75aa4a`
* release branch: `master`
* remote: `origin/master`
* Gateway version: `0.22.0`
* readiness: `ready`
* listener: `0.0.0.0:8000`
* frontend: HTTP 200 and container health `healthy`
* Alembic revision: `20260731_0018`
* scheduled supervisor: running with startup and sign-in triggers

The pre-deployment queue had zero queued and zero leased items. PostgreSQL was
backed up to:

```text
D:\workspace\cag\backups\releases\cag-pre-0.22.0-20260731-125626.dump
```

Backup size: 1,753,964,168 bytes.

## Historical correction

The migration changed `OI-6B26534BF5` from the contradictory historical
waiting-approval record to:

```text
plan_revision_required
revision_required
agent_self_improvement
revise
1 blocker
```

The issue was reopened once to execute the 0.22.0 planner and independent
Review. The resulting decision is:

* boundary `cag_internal`, 78 percent;
* implementation route `mixed`, 88 percent;
* Review recommendation `revise`;
* eight blockers;
* approval ready `false`;
* five proposed improvement areas;
* merged validation plan retained;
* version 2 plan and Review artifacts retained beside version 1.

The route is mixed because the present evidence proves a readiness threshold
breach without identifying its initiating cause. Immediate evidence capture and
controlled recovery need an authorized operator. Agent implementation becomes
appropriate for a reproducible CAG defect. Restart policy, readiness semantics,
timeouts and dependency handling retain human engineering approval.

A production approval request against the blocked issue returned HTTP 409. The
issue remained `plan_revision_required`.
