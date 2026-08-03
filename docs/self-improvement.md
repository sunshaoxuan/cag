# Controlled self-improvement

## Goal

CAG separates conversational continuity from reusable capability improvement.

Conversation history answers the next message with the same context. Durable improvement changes future behavior across Conversations by updating instructions, Skills, validators or runners after evidence and approval.

## Durable identity layers

1. `Conversation.id` is the public CAG identity used by callers.
2. `Conversation.codex_thread_id` is the internal Codex history identity.
3. Global and project `AGENTS.md` files define durable operating rules.
4. Skills package reusable workflows, references, scripts and validators.
5. Installation receipts record approved capability changes and rollback steps.

## Candidate workflow

The current executable entrypoint is Runtime Profile `self-improvement-candidate`.

When selected, CAG creates:

```text
{AGENT_GATEWAY_SELF_IMPROVEMENT_ROOT}/outputs/cag-{task_id}
```

Only this task-specific directory is added to the Codex runtime workspace roots. CAG injects instructions requiring:

* `TASK_LEARNING_RECEIPT.md`
* task type
* reusable pattern
* failure or user correction
* candidate Skill
* candidate Validator
* installation status
* evidence paths
* trigger, input, process, output, acceptance and rollback

The installation status stays `proposed`.

## Closed loop

```text
Task evidence and user correction
  |
Candidate generation
  |
Static validation
  |
Replay evaluation on representative tasks
  |
Promotion Service policy decision
  |
Install into project or user capability directory
  |
Installation receipt
  |
Monitor later task outcomes
  |
Rollback when acceptance regresses
```

## Operational issue entrypoint

Version 0.22.5 uses the self-operations issue center as the universal failure
entrypoint. Task-learning signals continue to discover repeated capability
patterns. Runtime failures first become an `OperationalIssue` with immutable
occurrences, a responsibility boundary, an AI plan and an independent Review.

The issue lifecycle is:

```text
detected
  |
triaging
  |
waiting_approval or plan_revision_required
  |
implementing or waiting_external
  |
evaluating
  |
closed or detected for the next cycle
```

An internal issue can create a `self-improvement-candidate` Task only after
administrator approval. The Task runs on an isolated improvement branch and
cannot push or merge through the issue workflow. External fixes can be recorded
individually or in batches and receive the same evaluation gate.

Administrator state transitions require a configured operations token and an
authenticated identity header. Runtime token deltas remain transient while
completed messages, tool activity and lifecycle evidence remain durable.

The administrator decision panel is always placed before the AI brief. The
occurrence counter communicates impact and does not determine authority.
Approval-ready plans may enter self-improvement. Pending, revision-required,
triage-failed and external-action cases can be rejected with a reason, closing
the current cycle without executing the proposed modification.

The planner also classifies the implementation route:

* `agent_self_improvement` for a bounded CAG change that the governed candidate
  workflow can implement after approval;
* `human_code_change` when direct engineering judgment or authority is needed;
* `external_operator_action` for credentials, infrastructure or external
  ownership;
* `mixed`, `out_of_scope` and `undetermined` for the remaining governed cases.

The issue detail stores a compact decision brief for administrators. Raw plans,
Reviews, command output and timeline events remain complete audit evidence.
Artifacts stay collapsed and timeline events load through bounded sequence
pages in the management screen. A malformed plan or Review,
`revise`, or any blocking finding produces `plan_revision_required` and keeps
the approval endpoint closed.

The backend publishes the current transition contract in `allowed_actions`.
Reopen is limited to terminal, failed and revision-required states. A new cycle
clears the prior mutable decision projection while preserving occurrences,
artifacts and event history. Controlled release checks end in
`validation_completed`.

Decision briefs and independent Reviews use Simplified Chinese for
administrator-facing prose. Technical identifiers and original error evidence
retain their source form. English-only or otherwise nonconforming primary
summary fields fail the language gate and receive a Chinese revision record.
Each planning cycle uses a new sequence-addressed read-only workspace so a
reopened issue examines the current default branch instead of a checkout from
an earlier plan.
If the planning runtime itself fails, the service writes a Chinese failure
brief, keeps the technical error as evidence, exposes a blocking finding and
keeps approval closed.

## Promotion state machine

```text
proposed
  |
validated
  |
benchmarked
  |
shadow after 10 successful runs
  |
canary after 5 successful runs
  |
active in the current Gateway registry
```

Benchmark promotion requires 20 isolated replay cases across two projects or
product versions, complete security and architecture checks, at least five
percent quality gain, no success rate regression, and a bounded P95 time
increase. Sensitive identifiers, secrets, raw prompts and private paths fail
the governance gate.

## Safety boundary

Candidate generation and installation are separate authorities.

The candidate task cannot overwrite formal Skills, formal rules or formal validators through the candidate output root. Formal activation is executed only by the Promotion Service and requires:

1. exact source candidate;
2. evaluation cases and results;
3. destination path;
4. approving user;
5. installation receipt;
6. rollback command or file restoration procedure.

The Codex credential store is outside all task workspace roots.

## Caller request

```json
{
  "project_id": "cag",
  "conversation_id": "UUID",
  "runtime_profile": "self-improvement-candidate",
  "prompt": "完成本轮工程任务，并把可复用流程整理为候选 Skill 和 Validator。"
}
```

The caller reads progress through the same CAG Conversation SSE endpoint. Candidate files are server-side artifacts until a later Artifact API exposes reviewed downloads.

## Implemented records and APIs

Version 0.7.0 persists CapabilityAsset, CapabilityEvaluation,
CapabilityPromotion, CapabilityRollback and GardenerRun. Public endpoints are
available under `/api/v1/capabilities`, `/api/v1/evaluations`,
`/api/v1/promotions`, `/api/v1/rollbacks` and `/api/v1/gardeners`.

An active asset is registered only in the current One Agent Gateway deployment.
The service does not modify another Codex installation. Every activation and
rollback writes a JSON receipt below
`D:\workspace\codex-selfimp\installation-receipts` when that root is configured.
