# ADR 0019: Continuous Windows supervision

## Status

Accepted for version 0.17.1, amended by ADR 0025 for version 0.23.0, updated
for dependency readiness in version 0.28.2 and periodic recovery in version
0.28.5.

## Context

The previous scheduled task had no trigger, no next run time and no failure
retry. The Gateway child could remain available after the scheduled action
reported `Ready`, while a later child exit left port 8000 offline.

The host runtime uses the locally installed Codex authenticated through the
current user's ChatGPT or API Key session. The supervisor therefore needs the
same interactive user identity.

## Decision

Task Scheduler starts a PowerShell supervisor at system startup and at current
user sign-in. A one-minute repeating watchdog trigger covers session lifecycle
interruptions that do not produce another startup or sign-in event. The task
has no execution time limit, ignores duplicate starts while the supervisor is
running and retries a failed supervisor every minute up to 999 times.

The supervisor checks port 8000, `/health/live` and `/health/ready` every 15
seconds. Four consecutive failed liveness checks restart only a process whose
command line matches the expected Uvicorn Gateway and port. Readiness requires
PostgreSQL storage, native pgvector search and Redis connectivity. Sustained
dependency failures are recorded without restarting a live API process. A
missing listener starts the normal managed launcher. An unexpected listener is
logged and left untouched.

PostgreSQL and Redis Compose services use `unless-stopped` restart policies so
Docker daemon recovery restores both stateful dependencies with their named
volumes.

The supervisor writes a 10 MiB rotating log and retains five historical files
under the ignored persistent Gateway workspace.

## Consequences

Gateway process exits recover automatically. Docker daemon recovery and stateful
dependency process exits are covered by the Compose restart policies. A
dependency that remains running while unready is recorded for operator action.
PostgreSQL queue leases preserve admitted work across recovery. Startup
continues to perform the guarded legacy migration, Redis readiness check and
frontend refresh.

Automatic startup that requires local Codex credentials becomes fully
operational when the configured Windows user has an interactive session.

## Validation

PowerShell parser and Pester checks cover all three triggers, retry settings,
listener identity checks, health thresholds and log rotation configuration. Runtime
acceptance checks the scheduled task state, trigger count, retry count,
supervisor process, all-interface listener, dependency container restart
policies, forced API-process recovery, readiness, health version and browser
console.

## Rollback

Run `manage-local-codex-gateway-task.ps1 stop` to stop supervision and the
recognized Gateway listener. Run it with `uninstall` to remove the scheduled
task. Restore the prior scripts to return to manual startup.
