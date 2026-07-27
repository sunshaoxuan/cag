# Phase 4 persistent conversation and self-improvement investigation

Date: 2026-07-27

Version: 0.4.0

## Question

How can an existing HTTP caller invoke the locally ChatGPT-authenticated Codex as one continuous agent, receive SSE from CAG, and produce controlled self-improvement candidates?

## Source to output chain

### Caller continuity

```text
POST /api/v1/conversations
  |
Conversation physical UUID
  |
POST /api/v1/tasks with the same conversation_id
  |
TaskExecutor reads Conversation.codex_thread_id
  |
first turn: thread/start with ephemeral false
later turn: thread/resume with stored thread ID
  |
turn/start in a new isolated Git clone
  |
Runtime notifications become TaskEvent rows
  |
Conversation-local event sequence
  |
GET /api/v1/conversations/{id}/events
  |
frontend EventSource
```

### Durable improvement

```text
runtime_profile = self-improvement-candidate
  |
Project YAML allowlist validation
  |
task-specific directory under codex-selfimp
  |
directory added to app-server runtimeWorkspaceRoots
  |
candidate and TASK_LEARNING_RECEIPT.md
  |
future replay evaluation and human approval
  |
formal installation receipt
```

## Protocol evidence

The installed Codex app-server generated the current JSON Schema bundle. `ThreadResumeParams` requires `threadId` and supports replacing `cwd`, `runtimeWorkspaceRoots`, sandbox and approval policy. `ThreadStartParams.ephemeral` controls whether history is materialized on disk.

The official app-server manual defines Thread as the conversation primitive and documents `thread/start`, `thread/resume`, `thread/fork` and streamed turn events:

* <https://learn.chatgpt.com/docs/app-server.md>
* <https://learn.chatgpt.com/docs/agent-configuration/agents-md.md>
* <https://learn.chatgpt.com/docs/build-skills.md>

## Corrections found during implementation

1. The Phase 3 runtime always used ephemeral threads, so `conversation_id` did not preserve Codex context.
2. The frontend SSE connection ended at Task completion, so it did not represent a continuous CAG Conversation.
3. Windows PowerShell 5 treated native `codex login status` standard error output as a terminating error under the script's strict error preference.
4. SQLite cannot add a foreign key through a direct `ALTER TABLE`; the migration requires Alembic batch mode.
5. A Task without a CAG Conversation must retain ephemeral Codex history to avoid orphaned persisted threads.
6. A self-improvement Task created before the release commit sees the last pushed `master` in its isolated clone. Candidate evidence must record the exact workspace commit.

## Live result

Conversation:

```text
e58d5430-bc13-4461-b71f-5ae5fbfea24a
```

Internal Codex thread:

```text
019fa10b-b0c1-74c3-873b-d4159816a3a4
```

First Task stored marker:

```text
CAG-PERSIST-7F3A91
```

Second Task ran in a different workspace, emitted runtime action `resumed`, and returned:

```text
CAG-PERSIST-7F3A91
```

Conversation SSE emitted continuous IDs 1 through 16. IDs 9 through 16 were retrieved with `after_sequence=8`.

## Boundary

CAG is the network and SSE control plane. Codex app-server remains a private child process. ChatGPT login state supplies runtime authentication. No API Key is part of the call chain.

## Candidate runtime result

A scoped `self-improvement-candidate` Task created `CANDIDATE.md` and `TASK_LEARNING_RECEIPT.md` under its assigned directory in `D:\workspace\codex-selfimp`. The project workspace stayed clean and the receipt retained `install_status: proposed`.

A broad candidate investigation against the last pushed 0.3.0 clone was terminated after prolonged dependency exploration. The failure supports adding cancellation, investigation budgets and workspace commit visibility to the later approval and evaluation control plane.
