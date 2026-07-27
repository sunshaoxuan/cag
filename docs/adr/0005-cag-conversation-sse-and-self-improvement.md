# ADR 0005: CAG owns conversation SSE and controlled self-improvement

Status: Accepted

Date: 2026-07-27

## Context

The Phase 3 adapter proved that an HTTP caller can invoke the locally ChatGPT-authenticated Codex app-server. Every Task still created an ephemeral Codex thread, and the frontend opened a Task-specific SSE stream that ended after one turn.

The caller requires continuous dialogue controlled by CAG. Reusable agent improvement also requires an auditable capability path outside temporary Task workspaces.

## Decision

1. CAG `Conversation.id` is the caller-visible continuous identity.
2. Each Conversation stores at most one opaque `codex_thread_id`.
3. The first Conversation Task calls `thread/start` with persistent history.
4. Later Conversation Tasks call `thread/resume`.
5. Tasks without a Conversation use ephemeral Codex threads.
6. CAG owns one Conversation SSE stream across multiple Tasks.
7. Conversation events use a durable Conversation-local sequence.
8. The app-server remains a private child process and never becomes the frontend SSE endpoint.
9. Self-improvement candidate generation uses a task-specific output root.
10. Candidate generation cannot install formal Skills, rules or validators.

## Consequences

The frontend can retain one EventSource while every turn continues to receive an isolated Git workspace. Conversation history remains in the local Codex store selected by `CODEX_HOME`.

Only one active Task is accepted per Conversation. This prevents two child app-server processes from concurrently advancing the same Codex thread.

The candidate profile creates auditable files and receipts. Durable proposal records, replay evaluation, approval and installation remain Phase 7 work.

## Evidence

The 0.4.0 live smoke created one CAG Conversation, completed two Tasks in different Git clones, observed `started` and `resumed` runtime events, and received the first-turn random marker from the second turn.
