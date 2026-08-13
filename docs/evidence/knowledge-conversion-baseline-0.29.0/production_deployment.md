# Production deployment

## Database

The existing PostgreSQL 16 database was migrated transactionally through
`20260813_0027` to `20260813_0028`. The migrations add baseline and manifest
planning tables plus sanitized failed-run evidence only.

## Runtime

The existing `CAG Local Codex Gateway` scheduled task was restarted through the
managed task script. Final state:

```text
version=0.29.0
status=ready
listener=0.0.0.0:8000
supervisor=Running
backend=postgresql
pgvector=0.8.2
frontend=http 200
```

## Data preservation

Before and after the largest-Source dry run:

```text
source_entries=115693
documents=22552
chunks=183091
embedding_cache=623429
code_symbols=496
code_relations=893
memory_candidates=143
```

Only the new planning tables received dry-run records.
