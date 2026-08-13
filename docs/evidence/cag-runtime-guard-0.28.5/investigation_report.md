# CAG 0.28.5 continuous runtime investigation

## Objective

Keep the formal CAG host runtime available after process failure, host session
interruption and Docker Desktop recovery.

## Findings

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| The formal Gateway and management UI were offline at investigation start | No listeners on ports 8000 or 5173; all five historical CAG scheduled tasks were `Ready` rather than `Running` | high | Point-in-time host observation |
| The registered supervisors ended together during the previous host lifecycle interruption | Last run was 2026-08-12 09:36 and result was `0xC000013A`; supervisor log stopped at the same time | high | Windows did not preserve a more specific application exception |
| Startup and sign-in triggers alone left a recovery gap | The interactive session continued without another startup or sign-in event and port 8000 remained offline | high | Resume behavior depends on Windows session lifecycle |
| PostgreSQL container health alone did not prove host connectivity | Container `pg_isready` passed while host Python timed out against `127.0.0.1:5432`; restarting CAG PostgreSQL and Redis containers restored host connectivity without replacing volumes | high | Docker Desktop forwarding is outside CAG process control |
| The existing supervisor recovers an API process failure | Verified Uvicorn PID 32548 was terminated and Ready returned with PID 31592 in about 45 seconds | high | This acceptance did not reboot Windows |
| Version 0.28.5 closes the no-new-event supervisor gap | Formal task has startup, sign-in and one-minute repeating triggers; `MultipleInstances=IgnoreNew` and `RestartCount=999` | high | Local Codex runtime still requires the configured interactive user's valid authentication session |

## Implemented change

The formal scheduled task now includes a one-minute repeating watchdog trigger
for ten years. Existing startup and sign-in triggers remain. Duplicate starts
are ignored while the supervisor is healthy. The release version and relevant
requirements, design, API and deployment documents were updated to 0.28.5.

## Runtime result

The formal host runtime reports Ready version 0.28.5 with PostgreSQL, pgvector
0.8.2 and Redis available. The management UI returns HTTP 200 on port 5173.
Browser DOM shows v0.28.5, the Browser console has zero warnings and errors,
and `browser-home.png` records the accepted page.
