# Phase 3 test results

Date: 2026-07-27

Version: 0.3.0

## Automated tests

Backend result:

```text
26 passed
Total coverage: 91.66 percent
```

The Fake app-server fixture covers:

* Protocol initialization.
* ChatGPT account acceptance.
* API Key account rejection.
* Thread and turn creation.
* Plan, command, file change, warning and agent message mapping.
* Approval callback decline and audit events.
* Unsupported server requests.
* Invalid JSONL rejection.
* Runtime provider configuration validation.

Frontend result:

```text
3 passed
Vite production build passed
```

## Direct local app-server smoke

The installed local executable reported a ChatGPT account type through `account/read`. A read-only ephemeral turn completed and returned:

```text
LOCAL_CODEX_SUBSCRIPTION_OK
```

No API Key was supplied.

## Gateway live subscription smoke

The host Gateway was started on loopback with `codex-app-server`, the configured Project registry and a task-local workspace root.

The first attempt reached `runtime.connected` and exposed a protocol negotiation requirement:

```text
thread/start.runtimeWorkspaceRoots requires experimentalApi capability
```

The client capability was enabled and the same live path was retested.

Final result:

```text
Task status: completed
Summary: GATEWAY_LOCAL_CODEX_SUBSCRIPTION_OK
Workspace commit: c6dd5ad2dc99089810d25a51e8dd8b07add64ef3
```

Observed events:

```text
task.created
task.started
workspace.preparing
workspace.ready
runtime.connected
agent.message
task.completed
```

The temporary host Gateway was stopped after validation.

## Launch script validation

`scripts/run-local-codex-gateway.ps1` passed PowerShell parsing, found the plugin app-server executable, verified ChatGPT login status, started version `0.3.0` on loopback port 8002 and returned a ready health response. The validation process was stopped afterward.

## Default Compose validation

The `0.3.0` frontend and Gateway images rebuilt successfully. Frontend, Gateway, PostgreSQL and Redis became healthy. Container configuration reported runtime provider `fake`, and a live Compose task completed through Fake Runtime. This confirms that container startup does not attempt to copy or use host ChatGPT credentials.
