# Phase 3 investigation report

Date: 2026-07-27

Version: 0.3.0

## Objective

Implement and verify the runtime boundary requested by the user: local Codex authenticated through the existing ChatGPT subscription session.

## Protocol evidence

The installed `codex-cli 0.146.0-alpha.3.1` generated its current app-server JSON Schemas. The required path uses:

```text
initialize
initialized
account/read
thread/start
turn/start
item and turn notifications
```

`account/read` distinguishes `chatgpt` from `apiKey`. The Gateway requires `chatgpt`.

## Implementation evidence

`CodexAppServerRuntime` starts a stdio child process, initializes the protocol, validates authentication, starts an ephemeral thread in the task workspace, starts a turn and maps notifications into durable events.

The adapter does not open `auth.json`, copy credentials, inspect tokens or expose account email.

## Live evidence

A direct app-server turn and a full Gateway HTTP task both completed through the locally signed-in ChatGPT account. The Gateway task cloned the published repository into its independent workspace and recorded the starting commit.

## Protocol correction

The first Gateway smoke declared `experimentalApi` as false while sending `runtimeWorkspaceRoots`. The installed server rejected this combination. The capability is now declared true, matching the generated schema and observed server behavior.

## Remaining scope

* Phase 4 defines runtime profiles and command policy centrally.
* Phase 5 persists approvals and resumes suspended turns.
* Conversation-to-thread persistence is pending.
* The default Compose path remains Fake Runtime.
* A credential-safe host bridge is required before containerized real-runtime deployment.
