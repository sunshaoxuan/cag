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
Human review and approval
  |
Install into project or user capability directory
  |
Installation receipt
  |
Monitor later task outcomes
  |
Rollback when acceptance regresses
```

## Safety boundary

Candidate generation and installation are separate authorities.

The candidate task cannot overwrite formal Skills, formal rules or formal validators through the candidate output root. Formal installation remains a future approval API and requires:

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

## Remaining implementation

Phase 7 will add durable `SkillProposal`, `EvaluationRun`, approval and installation receipt records. It will also add replay datasets, automated validators and rollback status. Current 0.4.0 provides the restricted candidate-writing execution path and documented human gate.
