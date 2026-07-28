# Current release receipt

Version: 0.8.1

Date: 2026-07-28

Branch: `master`

## Delivered

* The local ChatGPT-authenticated Gateway binds to `0.0.0.0` by default.
* The managed background task detects a listener by port.
* Starting the managed task replaces an existing loopback-only listener.
* Managed startup verifies that the ready process listens on `0.0.0.0` or `::`.
* Status output includes the actual listener address.
* The root workspace ignore rule no longer excludes the backend Workspace
  Manager module from Git.
* Version, changelog, requirement matrix, architecture, deployment, security,
  API and operator documentation are aligned with the listener behavior.

## Verified

* 6 PowerShell listener tests passed.
* 62 backend tests passed with 88.69 percent coverage.
* 8 frontend tests and the production build passed.
* Docker Compose configuration validation passed.
* The live managed process reported `0.0.0.0:8000`.
* Readiness passed through loopback and a non-loopback host IPv4 address.
* The live health response reported version `0.8.1`.

## Security boundary

The Gateway HTTP listener is reachable through all IPv4 host interfaces.
Caller authentication, project authorization, HTTPS and distributed rate
limiting remain open production gates. Codex app-server and Ollama retain their
private local boundaries.

## Rollback

Revert the 0.8.1 commit, restart the managed task and verify that the listener
returns to the prior loopback behavior. No database migration or data rollback
is required.
