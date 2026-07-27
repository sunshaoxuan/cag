# Enterprise knowledge test results

Date: 2026-07-27

## Automated

| Command | Result |
|---|---|
| `backend\.venv\Scripts\python.exe -m pytest` | 43 passed, 87.02 percent coverage |
| `pnpm test` | 5 passed |
| `pnpm build` | Passed |
| `docker compose config --quiet` | Passed |
| `alembic upgrade head` against PostgreSQL | `20260727_0005` |

## Real local smoke

| Check | Result |
|---|---|
| Ollama version | 0.23.3 |
| Listener | `127.0.0.1:11434` |
| GPU | NVIDIA GeForce RTX 5070 Ti |
| Models | `qwen3-embedding:8b`, `qwen3:14b` |
| Source ingestion | 1 file, 1 encrypted vector chunk |
| Cold search | 1 result, 2003 milliseconds |
| Task knowledge injection | 1 citation |
| Memory extraction | 1 candidate |
| Ingestion SSE | queued and completed events present |
| Task SSE | context injection and memory completion present |

The smoke Task used Fake Agent Runtime and real local Ollama. It consumed no Codex or OpenAI API quota. Smoke rows were removed because their encryption key was intentionally ephemeral.
