# Final acceptance checklist

| Original intent or constraint | Artifact and evidence | Result |
|---|---|---|
| CAG is currently running | `/health/ready` returns 0.28.5 Ready; port 8000 listens on all IPv4 interfaces | PASS |
| Management UI is available | Port 5173 returns HTTP 200; Browser DOM and screenshot render the homepage | PASS |
| Process failure recovers automatically | Controlled Uvicorn termination recovered to a new PID and Ready | PASS |
| Supervisor interruption recovers without another login | One-minute repeating watchdog trigger is installed | PASS |
| Stateful dependencies survive recovery | PostgreSQL and Redis retain named volumes and `unless-stopped`; host connectivity verified | PASS |
| No duplicate supervisors are created | Scheduled task uses `MultipleInstances=IgnoreNew` | PASS |
| Runtime remains tied to local Codex authentication | Existing `codex-app-server` host runner contract is unchanged | PASS |
| Requirements and architecture records match behavior | VERSION, CHANGELOG, README, requirements matrix, ADR, API and deployment documents updated | PASS |
| Relevant tests pass | Backend, Pester, frontend and build results recorded in `test_results.md` | PASS |
| UI acceptance is real | Browser DOM, Console and screenshot evidence recorded | PASS |
| Work stays on master and is delivered to origin/master | Release commit is created on master; remote equality is verified immediately after push | PASS |
