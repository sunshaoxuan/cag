# ADR 0006: Truthful runtime feedback and frontend projection

## Status

Accepted.

## Context

The local Codex app-server emits user-visible message deltas, plan deltas, command output deltas and reasoning-summary deltas while a turn is running. CAG previously accumulated agent-message deltas in memory and only persisted a completed `agent.message`. The event panel could show completed progress messages while the conversation bubble remained in its initial queued state.

The backend is the audit boundary. It must preserve every permitted user-visible feedback event in order. A frontend may choose a smaller projection without changing backend fidelity.

## Decision

1. CAG persists and streams these app-server notifications without dropping their text:
   * `item/agentMessage/delta` as `agent.message.delta`
   * `item/plan/delta` as `agent.plan.delta`
   * `item/commandExecution/outputDelta` as `command.output.delta`
   * `item/reasoning/summaryTextDelta` as `agent.reasoning.summary.delta`
2. Each delta event retains its app-server item identity, turn identity and exact delta. Agent-message delta events also contain the cumulative text for that message item so reconnecting clients can replace their current projection deterministically.
3. Completed `agent.message`, `agent.plan`, `command.completed` and `task.completed` events remain authoritative snapshots.
4. Hidden reasoning text, credential material and unsupported raw notifications are not exposed as CAG feedback.
5. The React console consumes every named event required for task integrity. Its feedback controls select the visible event categories and the maximum number of rows. These controls do not alter the durable backend event history.
6. The active conversation bubble consumes `agent.message.delta` and `agent.message` independently of the event-panel filter, updates the Task projection to running and replaces the live text with the final report on `task.completed`.

## Frontend projection

The console provides:

* `关键反馈`: completed Agent messages, runtime thread changes, completed commands or tests and terminal Task events.
* `标准反馈`: all structured lifecycle events except high-volume deltas.
* `完整反馈`: every supported CAG event including deltas.
* A display limit of 20, 50, 100 or all visible rows.

The panel always reports both the number of events received from CAG and the number currently displayed.

## Consequences

* CAG retains a faithful, replayable event sequence.
* High-volume delta traffic increases TaskEvent writes and SSE traffic.
* Frontends can reduce rendering cost without asking the backend to discard evidence.
* Raw hidden reasoning remains outside the public contract.

## Acceptance

1. Runtime unit tests prove exact delta mapping and item identity.
2. Conversation SSE tests prove delta events are ordered and resumable.
3. Frontend tests prove live message replacement, running-state updates, feedback filtering and display limits.
4. A real ChatGPT-authenticated Codex turn shows message deltas before `task.completed`.
5. Browser validation shows the live conversation bubble, configurable feedback controls, zero console errors and the final authoritative answer.

## Rollback

Remove the new event mappings and frontend controls, revert this ADR and redeploy the previous commit. Existing TaskEvent rows remain readable because event types are strings and no schema downgrade is required.
