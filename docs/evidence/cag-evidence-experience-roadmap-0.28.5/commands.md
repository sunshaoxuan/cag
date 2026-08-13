# Commands

## Repository and model inspection

```powershell
git status --short
git branch --show-current
git log -1 --oneline
rg -n "extractor|processing_status|MemoryCandidate|KnowledgeChunk" backend docs
```

## Production read-only inspection

The running `cag-postgres-1` container was queried with `psql` for relation
sizes, table counts, Source Entry processing states, ingestion status and
rejection reason distributions. No production row was modified.

Observed headline values were:

```text
database_size=11 GB
knowledge_source_entries=113908
knowledge_documents=22552
knowledge_chunks=183091
knowledge_embedding_cache=623429
memory_candidates=143
main_source_observed=69367
main_source_metadata_only=43910
main_source_indexed=460
main_source_rejected=132
active_ingestion=1 scheduled running
```

## Documentation validation

```powershell
git diff --check
Select-String roadmap and ADR for required architecture, phase, acceptance and rollback terms
rg -n '[—–]' changed formal documents
rg -n '不是.+而是|不.+而是' changed formal documents
```

## Required backend test

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Final result: 193 passed, 4 skipped, 85.24 percent coverage.
