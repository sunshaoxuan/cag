# Enterprise knowledge investigation report

## Question

Can the current machine and Agent Gateway run a private, governed RAG plane that supports reusable product knowledge without replacing the ChatGPT-authenticated Codex runtime?

## Verified environment

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| Ollama runs in Docker with GPU access | Container log reports RTX 5070 Ti, CUDA compute 12.0 and 15.9 GiB VRAM | high | One GPU |
| Required models already exist | `/api/tags` returns `qwen3-embedding:8b` and `qwen3:14b` | high | Text and code only |
| Ollama is private to the host | Docker publishes `127.0.0.1:11434` | high | Local administrators retain access |
| PostgreSQL supports vectors | `pg_extension` reports vector 0.8.2 and HNSW index exists | high | Host storage is not BitLocker encrypted |
| Existing database survived migration | Project, Conversation and Task counts remained 3, 1 and 11 | high | Backup retained during implementation |

## Behavior path

```text
Knowledge Source API
  |
allowed root and scope validation
  |
text file scan and secret redaction
  |
encrypted chunks and Ollama embeddings
  |
PostgreSQL pgvector
  |
tenant and product authorization filters
  |
vector and keyword reciprocal rank fusion
  |
approved evidence package
  |
TaskExecutor developer instructions
  |
Codex or Fake Agent Runtime
  |
local memory candidate extraction
```

## Risks

* C and D drives have no BitLocker protection. Search indices remain a production admission warning.
* External users still require authentication and project authorization.
* The initial hybrid search implementation computes candidate similarity in the application after scope filtering. The HNSW index is ready for the larger corpus query path.
