# ADR 0007: Governed enterprise RAG belongs to Agent Gateway

Status: Accepted

## Decision

CAG owns source registration, tenant authorization, indexing, retrieval, citations, memory governance and SSE. Ollama is a private local inference dependency. Codex receives only approved, bounded evidence through the existing runtime adapter.

PostgreSQL with pgvector stores 1024 dimensional embeddings and durable governance records. Source and memory text is encrypted. Strong references use physical UUID foreign keys.

## Consequences

Different customers can reuse approved ProductVersion knowledge without accessing one another's tenant memory. Model replacement requires a complete dimension-compatible reindex. Knowledge outages are explicit through Task mode and SSE. Full external deployment remains blocked by authentication and encrypted-host-storage requirements.
