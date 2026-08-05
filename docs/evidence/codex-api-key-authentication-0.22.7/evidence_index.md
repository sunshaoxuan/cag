# Evidence index

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| CAG starts the Codex Agent work process | `backend/app/main.py` constructs `[codex_executable, "app-server", "--stdio"]` | high | Runtime executable is host-configured |
| API Key authentication is accepted | `backend/app/runtimes/codex_app_server.py`, `test_codex_app_server_runtime.py` | high | Fixture and live evidence cover the current protocol shape |
| Empty `account` API Key response is accepted | `account/read` mapping for `requiresOpenaiAuth=false` and dedicated test | high | The response shape is supplied by the installed Codex version |
| Real API Key Agent task completed | Task `8e752931-0ebf-4438-9302-d53fb0ffaf67`, `runtime.connected` and `task.completed` events | high | The task used the current local Codex login state |
| CAG does not directly call OpenAI APIs | Source scan result `NO_DIRECT_OPENAI_CALLS_IN_CAG_RUNTIME`; no `OPENAI_API_KEY` in Gateway process, user or machine environment | high | Static scan does not inspect external binaries |
| ChatGPT-only policy remains available | `AGENT_GATEWAY_CODEX_REQUIRE_CHATGPT_AUTH=true` branch and test | high | The managed launcher intentionally defaults to both modes |
| Gateway is published on all IPv4 interfaces | `/health/ready`, `Get-NetTCPConnection`, launcher and Pester test | high | Host firewall remains an external deployment control |
| PostgreSQL, Redis and pgvector are healthy | `/health/ready` returned `ready`, `redis_connected=true`, `backend=postgresql`, `native_vector_search=true` | high | Health is a point-in-time observation |
