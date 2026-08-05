# ADR 0001: Use local Codex authentication

Status: Superseded by ADR 0024 for the current authentication policy

Date: 2026-07-27

## Context

The original Phase 1 boundary required the Codex/ChatGPT capability already available on the local machine through a ChatGPT subscription. The current policy is defined by ADR 0024 and adds Codex API Key login support.

The official Codex documentation states that ChatGPT sign-in provides subscription access for local Codex clients. It also states that `codex exec` reuses saved CLI authentication and that `codex app-server` is intended for deep product integrations needing authentication, conversation history, approvals and streamed events.

## Decision

Use a local Codex adapter with this priority:

1. `codex app-server` over stdio JSONL for production integration.
2. `codex exec --json` for a controlled compatibility path.
3. `FakeAgentRuntime` for automated tests.

The Gateway never requires `OPENAI_API_KEY` in its default configuration.

## Verified local evidence

On 2026-07-27:

* Executable: `C:\Users\Administrator\.codex\plugins\.plugin-appserver\codex.exe`
* Version: `codex-cli 0.146.0-alpha.3.1`
* Login result at the time: `Logged in using ChatGPT`
* `codex app-server --help` exposes stdio, Unix socket and WebSocket transports.
* `codex exec --help` exposes JSONL, output schema, sandbox, working directory and resume functions.

The WindowsApps desktop executable cannot be started directly from the current PowerShell process because Windows denies that entry point. The plugin app-server CLI is directly executable and provides the required capabilities.

## Security consequences

* Codex credentials remain in Codex-managed local storage.
* The Gateway does not inspect credential contents.
* Codex runs on a trusted host boundary.
* Task containers do not receive the host credential store.
* App-server uses stdio by default.
* Approval and sandbox configuration are explicit per runtime profile.

## Compatibility consequence

App-server schemas are generated from the installed Codex version and stored with the Gateway adapter tests. Version upgrades require schema regeneration and adapter compatibility tests.

## Historical rejected option

Direct Responses API integration with a CAG-managed `OPENAI_API_KEY` belongs to a separate deployment mode and remains outside the default architecture.

## Rollback

Set the runtime provider to `fake` and disable local Codex task admission. Existing Task and TaskEvent records remain readable.
