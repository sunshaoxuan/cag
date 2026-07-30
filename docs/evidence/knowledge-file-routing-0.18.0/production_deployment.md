# Production deployment

## Release identity

* version: `0.18.0`
* source commit: `f26a0989525be5ebe8f1f85eaf13ea8acb1f644d`
* deployment date: 2026-07-30
* managed task: `CAG Local Codex Gateway`

## Cutover gate

One interactive queue item was actively heartbeating when publication was
requested. The release waited for Task
`1bbe7a66-d69d-41c8-b670-85e9755974a4` to complete. Immediately before
shutdown:

* active queue items: 0
* active Tasks: 0
* active knowledge ingestions: 0
* Alembic revision: `20260729_0014`
* knowledge documents: 21,772
* knowledge chunks: 170,807

## Backup

The PostgreSQL custom-format backup is:

`D:\workspace\cag\backups\releases\0.18.0-20260730T0814Z\agent_gateway-pre-0.18.0.dump`

* size: 1,743,713,587 bytes
* SHA256: `DFB5759A1FDBF1FA3D8EEDD971A6F2E1087FFCF1D2F8BE3E80570B81189BBF6A`

## Managed restart

The task manager stopped the supervised listener and registered or started the
same long-running task. The launcher:

1. verified local ChatGPT-authenticated Codex;
2. verified PostgreSQL and pgvector;
3. applied Alembic `20260730_0015`;
4. checked the existing SQLite migration receipt;
5. verified Redis;
6. rebuilt and replaced only the frontend container;
7. started Uvicorn on `0.0.0.0:8000`.

The manager returned ready in 43.8 seconds. The supervisor log recorded the
new PID 29400 ready at 17:17:23 local time.

## Post-migration validation

| Check | Result |
|---|---|
| Gateway live version | 0.18.0 |
| Ready database backend | PostgreSQL |
| Alembic revision | 20260730_0015 |
| pgvector | 0.8.2 |
| Listener | 0.0.0.0:8000 |
| Frontend | healthy on 5173 |
| Knowledge documents | 21,772 |
| Knowledge chunks | 170,807 |
| Rejection file size | bigint |
| Source entry file size | bigint |
| Local models | qwen3-embedding:8b and qwen3:14b |
| Scheduler | running, 10-second poll |
| LAN API | 192.168.20.54:8000 returned 0.18.0 |
| LAN UI | 192.168.20.54:5173 returned HTTP 200 |
| Browser console | no captured errors |

## Live learning after release

The scheduler immediately found due sources. One small source attempted before
Ollama had been restarted and entered the normal bounded retry schedule. After
Ollama became ready, `UPDS顧客別情報` began scanning with the 0.18.0 policy.

At the sampled progress point:

* ingestion ID: `6dca03fb-0df7-4401-a6f5-c861894accb5`
* event sequence: 522
* directories scanned: 259
* directories pending: 719
* files discovered and processed: 768
* skipped file outcomes: 304
* rejected file outcomes: 54

This ingestion remains active and is intentionally left running.

At 17:24:19 local time the scheduler created retry ingestion
`deb4ce91-a6ad-48a4-94ae-034ecf4b70be` for the source that encountered the
brief Ollama outage. It is durably queued behind the active UPDS ingestion.
This confirms the bounded retry path without interrupting the current scan.

## Rollback

1. Let active Task and ingestion work reach a terminal state.
2. Stop `CAG Local Codex Gateway`.
3. Restore the custom-format backup into a separate PostgreSQL database.
4. validate table counts, pgvector extension and vector dimensions.
5. update the ignored local database URL only after validation.
6. start the managed task and verify health and listener address.

The active production database has not been overwritten by the backup.
