# Current release test results

Date: 2026-07-28

Version: 0.8.1

## Automated

| Check | Result |
|---|---|
| PowerShell script parsing | Passed for both local Gateway entrypoints |
| PowerShell listener regression | 6 passed |
| Backend Pytest | 62 passed |
| Backend coverage | 88.69 percent |
| Frontend Vitest | 8 passed |
| Frontend production build | Passed |
| Compose configuration | Passed |

The first complete backend run found stale `0.8.0` assertions and package
metadata. Those release fields were updated to `0.8.1`, and the complete suite
then passed.

An isolated staged-tree run found that the repository-wide `workspaces/`
ignore rule also excluded `backend/app/workspaces/manager.py`. The rule was
restricted to `/workspaces/`, the existing runtime module was added to version
control, and the isolated staged-tree suite was rerun.

## Live all-interface listener

The managed local Codex Gateway was restarted from the prior loopback listener.
Windows reported the active socket as `0.0.0.0:8000`.

| Probe | Result |
|---|---|
| Managed task state | `running` |
| Managed task listener | `0.0.0.0:8000` |
| Windows TCP listener | `0.0.0.0:8000` |
| Loopback readiness | `ready` |
| Non-loopback IPv4 readiness | `ready` |
| Reported Gateway version | `0.8.1` |

The non-loopback check called `/health/ready` through a preferred host IPv4
address. This verifies the process binding on the current host. Inbound access
from another machine still depends on the host firewall and surrounding
network.
