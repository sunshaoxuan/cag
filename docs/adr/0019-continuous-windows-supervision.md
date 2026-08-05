# ADR 0019: Continuous Windows supervision

## Status

Accepted for version 0.17.1.

## Context

The previous scheduled task had no trigger, no next run time and no failure
retry. The Gateway child could remain available after the scheduled action
reported `Ready`, while a later child exit left port 8000 offline.

The host runtime uses the locally installed Codex authenticated through the
current user's ChatGPT or API Key session. The supervisor therefore needs the
same interactive user identity.

## Decision

Task Scheduler starts a PowerShell supervisor at system startup and at current
user sign-in. The task has no execution time limit and retries a failed
supervisor every minute up to 999 times.

The supervisor checks port 8000 and `/health/ready` every 15 seconds. A missing
listener starts the normal managed launcher. Four consecutive failed readiness
checks restart only a process whose command line matches the expected Uvicorn
Gateway and port. An unexpected listener is logged and left untouched.

The supervisor writes a 10 MiB rotating log and retains five historical files
under the ignored persistent Gateway workspace.

## Consequences

Process exits and sustained health failures recover automatically. PostgreSQL
queue leases preserve admitted 0.17 work across recovery. Startup continues to
perform the guarded legacy migration, Redis readiness check and frontend
refresh.

Automatic startup that requires local Codex credentials becomes fully
operational when the configured Windows user has an interactive session.

## Validation

PowerShell parser and Pester checks cover triggers, retry settings, listener
identity checks, health thresholds and log rotation configuration. Runtime
acceptance checks the scheduled task state, trigger count, retry count,
supervisor process, all-interface listener, health version and browser console.

## Rollback

Run `manage-local-codex-gateway-task.ps1 stop` to stop supervision and the
recognized Gateway listener. Run it with `uninstall` to remove the scheduled
task. Restore the prior scripts to return to manual startup.
