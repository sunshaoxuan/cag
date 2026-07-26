# Phase 2 investigation report

Date: 2026-07-27

Version: 0.2.0

## Objective

Implement configuration-driven projects, task-isolated Git workspaces, the expanded event lifecycle and a browser task console while preserving the local ChatGPT subscription runtime boundary.

## Findings

### Project identity

Project Code remains a business identifier. YAML declares an independent UUID physical ID, and Task foreign keys store that UUID.

### Workspace isolation

Two live container tasks received different workspace IDs and directories. Both cloned the configured `master` branch and recorded the same authoritative remote commit because they started from the same published repository state.

### Event lifecycle

The Phase 2 happy path produced eight ordered events:

```text
task.created
task.started
workspace.preparing
workspace.ready
agent.plan
agent.message
test.completed
task.completed
```

### Browser task console

The React console loaded the Project API, submitted a task, consumed named SSE events, presented the independent workspace state and rendered the structured final report. Browser console inspection reported no errors or warnings.

### Runtime clarification

The production target is the locally installed Codex using the existing ChatGPT subscription login. Phase 2 deliberately retains Fake Runtime for deterministic, quota-free validation. The actual app-server adapter and live subscription-backed smoke test belong to Phase 3.

## Remaining risk

* The real local Codex adapter is not yet enabled.
* The Compose Gateway cannot receive host Codex credentials by copying credential files.
* A host-side runtime bridge or host-executed Gateway boundary is required in Phase 3.
* Repository allowlisting, private repository credentials, workspace cleanup and resource quotas remain open.
* Authentication and project authorization remain production blockers.
