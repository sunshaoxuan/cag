# Production deployment

## Backup

The custom format PostgreSQL backup is:

`D:\workspace\cag\backups\releases\0.23.0-20260806T040404Z\agent_gateway-pre-0.23.0.dump`

`pg_restore -l` read the backup successfully. Size is 1,776,349,708 bytes.

## Database

Production Alembic revision is `20260806_0021`. Extensions `vector` and
`pg_trgm` are installed. Trigram indexes exist for Chunk search text and
document path. Code symbol name indexes are also created by Migration 0021.

## Runtime

The managed Windows task listens on `0.0.0.0:8000`. Readiness reports process
role `api`, PostgreSQL native vector search, pgvector 0.8.2 and Redis connected.
Queue workers run in a separate process and the API has no local consumers.

## Knowledge state

UPDS Source `c4837509-0c4c-4689-bb34-e30a1138da05` remains approved with
active Generation `8c8c3326-c329-4828-8c04-ff41dd1d9e01`. The final scheduled
acceptance run was cancelled through the public Queue API. Its Source lease was
released and next sync advanced to 16:11:32 Japan time.

## Browser

The deployed frontend at `http://127.0.0.1:5173/knowledge` showed version
0.23.0, three Sources, Ollama ready, 1024 dimensions, approved UPDS knowledge
and zero active runs. Browser Console warnings and errors were zero. Screenshot:
`knowledge-page.png`.
