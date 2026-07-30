# Version 0.17.1 evidence index

| Evidence | Purpose |
|---|---|
| `scripts/supervise-local-codex-gateway.ps1` | Continuous listener and health supervision |
| `scripts/manage-local-codex-gateway-task.ps1` | Startup triggers, retry policy and lifecycle actions |
| `scripts/tests/LocalCodexGateway.Tests.ps1` | Parser and supervision configuration tests |
| `docs/adr/0019-continuous-windows-supervision.md` | Runtime identity and recovery decision |
| `backups/knowledge-migrations/auto-20260730T035339Z-8299cc3761c1` | Local migration reports retained outside Git |
| `workspaces/.gateway/logs/gateway-supervisor.log` | Local rotating supervisor runtime log |
| `docs/evidence/screenshots/continuous-supervision-0.17.1.png` | Browser version and management-page evidence |
| `test_results.md` | Automated and runtime validation |
| `FINAL_RECEIPT.md` | Deployment and rollback receipt |
