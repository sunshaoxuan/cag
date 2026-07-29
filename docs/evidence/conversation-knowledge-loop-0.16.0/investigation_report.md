# One Agent Gateway 0.16.0 Conversation knowledge loop investigation

## Question

Determine whether Conversation SSE tasks first use learned knowledge and whether
the retrieved fragments and original resource links reach Codex app-server.
Complete the source, analysis, answer and memory evidence loop where required.

## Findings before implementation

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| Retrieval already ran before runtime execution | `backend/app/tasks/executor.py` called `build_context()` before `runtime.execute()` | High | The contract was not expressed as a resource-linked loop |
| Knowledge fragments already reached Codex | `developer_instructions` was passed to `thread/start` and `thread/resume` | High | Blocks exposed relative path and commit only |
| Conversation SSE already reported injection metadata | `knowledge.context.injected` contained citations | High | Citations had no resource URI |
| Memory extraction already followed Task completion | `capture_memory()` used prompt and final report | High | Candidate evidence stored only Task ID |

## Implemented result

Version 0.16.0 keeps governed retrieval before every default assisted
Conversation turn. Selected fragments now carry source name, source type,
canonical path, commit and source-specific `resource_uri` into Codex
app-server developer instructions.

The same structured citation objects are persisted in KnowledgeUsage, emitted
through Conversation and Task SSE, attached to the Task final report and stored
in MemoryCandidate evidence. Codex instructions require learned evidence to be
analyzed first and relevant resource URIs to be cited in the answer.

## Safety boundary

Source approval, tenant or product authorization, prompt-injection exclusion
and context limits still run before injection. Resource URI generation does not
include credentials. Knowledge plaintext remains outside SSE and audit
payloads.

## Runtime limitation

The live 8000 process was not restarted because the existing long knowledge
ingestion must continue naturally. Browser validation used an isolated 5174
frontend container connected to the existing Gateway. Codex protocol delivery
was verified with the deterministic app-server fixture and did not consume
subscription quota.
