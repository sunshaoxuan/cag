# ADR 0004: Local app-server authentication

Status: Superseded by ADR 0024 for the current authentication policy

Date: 2026-07-27

## Context

The original Phase 3 implementation used the locally installed Codex authenticated by the user's ChatGPT subscription. API Key login support is now defined by ADR 0024.

Codex app-server exposes a JSONL protocol for account state, threads, turns, approvals and streamed items.

## Decision

Phase 3 starts one `codex app-server --stdio` child process per task on the trusted host.

The adapter:

1. Sends `initialize` and the `initialized` notification.
2. Calls `account/read`.
3. Accepts account type `chatgpt` or `apiKey`; current API Key sessions can report an empty account with `requiresOpenaiAuth=false`.
4. Starts an ephemeral thread in the isolated task workspace.
5. Sets `runtimeWorkspaceRoots` to that workspace.
6. Starts one turn with the task Prompt.
7. Maps app-server notifications to Gateway events.
8. Stores the final agent message as the task summary.
9. Terminates the child process after completion.

`runtimeWorkspaceRoots` requires the app-server experimental API capability in the installed protocol version. The client declares that capability during initialization.

Phase 3 uses approval policy `never`. Approval callbacks are declined and recorded until the durable approval lifecycle is implemented.

## Consequences

* The Gateway reuses the current local Codex login.
* CAG does not read or store the API Key.
* Credential files remain private to Codex.
* Each task has process-level failure isolation.
* Per-task process startup adds latency.
* Long-lived thread reuse and durable approval resume remain future work.
* The default container stays on Fake Runtime because host credentials are not copied into it.

## Rollback

Set `AGENT_GATEWAY_RUNTIME_PROVIDER=fake`, stop the host Gateway, and redeploy the previous release. No credential migration is required.
