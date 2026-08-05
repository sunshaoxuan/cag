# Investigation report: local Codex API Key authentication

## Objective

Verify that One Agent Gateway can use a local Codex installation logged in with
an API Key while preserving the Codex Agent work-process boundary. CAG must
continue to start `codex app-server --stdio`, create or resume Codex threads,
start turns, forward Agent events through CAG SSE, and keep credentials in the
local Codex credential boundary.

## Source to execution path

1. `scripts/run-local-codex-gateway.ps1` checks the local `codex login status`
   output for ChatGPT or API Key authentication and starts the Gateway with
   `AGENT_GATEWAY_RUNTIME_PROVIDER=codex-app-server`.
2. `backend/app/main.py` constructs the runtime command as the configured local
   executable followed by `app-server` and `--stdio`.
3. `backend/app/runtimes/codex_app_server.py` performs JSONL initialization,
   calls `account/read`, accepts `chatgpt` or `apiKey`, and maps the current
   empty-account API Key response (`requiresOpenaiAuth=false`) to `apiKey`.
4. The adapter calls `thread/start` or `thread/resume`, then `turn/start`, and
   maps Agent message, plan, command and completion notifications to durable
   CAG events.
5. CAG exposes those events through its task or Conversation SSE endpoint. The
   frontend does not connect to Codex app-server directly.

## Findings

The implementation preserves the intended Agent architecture. CAG does not
call the OpenAI Responses API or Chat Completions API. A source scan over
`backend/app`, `scripts` and `backend/pyproject.toml` returned
`NO_DIRECT_OPENAI_CALLS_IN_CAG_RUNTIME`.

The local API Key session was exercised through a real CAG task. The task
completed with summary `API_KEY_RUNTIME_SMOKE_OK`; its durable
`runtime.connected` event reported provider `local-codex-app-server` and
authentication `apiKey`. The task produced no file changes.

## Limitations and controls

The Gateway never reads or stores the API Key. Authentication validity remains
the responsibility of the local Codex process and its credential store. Setting
`AGENT_GATEWAY_CODEX_REQUIRE_CHATGPT_AUTH=true` retains a strict ChatGPT-only
deployment policy. The managed launcher defaults this setting to `false` so
both supported local Codex login modes work.
