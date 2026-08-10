# ADR 0031: Task Attempt Model Routing

## Status

Accepted on 2026-08-10.

## Context

OneOps configures separate physical Model settings for simple and general work. The AI assistant keeps one CAG Conversation so that later turns retain Codex Thread history. A Conversation can contain translation, inquiry analysis and Agent operations with different latency and reasoning requirements.

The official Codex app-server protocol supports `model` on `thread/start`, `thread/resume` and `turn/start`. It supports `effort` on `turn/start`. Resuming a stored Thread with a different Model retains the same Thread history and records the Model switch.

## Decision

1. OneOps owns business Task classification, Task Summary continuation, Task Fingerprint generation, Tier selection and repeated Task escalation.
2. CAG accepts optional `model`, `effort` and `routing_context` fields on Task creation.
3. CAG validates that `routing_context.model` and `routing_context.reasoningEffort` match the Runtime fields.
4. CAG stores the selection and Routing Context in the immutable Task request Metadata and the `task.created` event.
5. CAG applies the selected Model to both Thread start or resume and Turn start. It applies Reasoning Effort to Turn start.
6. Existing CAG Tasks without an explicit Model continue to use the Codex configuration selected by the local authenticated Runtime.
7. No new database column is introduced. Task request Metadata is the existing audit record for external immutable request attributes.

## Routing Context

The Context records Routing Policy Version, Task Class, objective summary, target language, constraints, continuation mode, Task Fingerprint, Attempt number, Tier, OneOps Model setting physical ID, OneOps Gateway setting physical ID, Model, Reasoning Effort, selection reason and escalation reason.

OneOps physical IDs are external audit references. CAG does not use OneOps Code or Model name as an internal foreign key.

## Acceptance

1. Task creation rejects a Routing Context whose Model or Effort differs from the Runtime selection.
2. Task and audit responses return the stored Runtime selection and Routing Context.
3. The deterministic app-server fixture verifies Model propagation on Thread resume and Turn start and Effort propagation on Turn start.
4. Existing Task API and Runtime tests remain green.

## Rollback

Revert this ADR and the Task API, Executor and app-server Runtime changes in the same commit. OneOps must stop sending the three Routing fields before the CAG rollback is delivered.
