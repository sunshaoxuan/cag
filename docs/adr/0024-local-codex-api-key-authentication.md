# ADR 0024: Support ChatGPT and API Key local Codex authentication

Status: Accepted

Date: 2026-08-05

## Context

The host Codex installation can be authenticated through ChatGPT or through a
Codex API Key. The Gateway previously required the launcher text
`Logged in using ChatGPT`, and the app-server adapter rejected every account
type other than `chatgpt`. A restart after switching to API Key authentication
therefore left the managed Gateway in a launcher retry loop while PostgreSQL
records remained intact.

## Decision

The managed host Gateway supports both local Codex authentication modes:

* `Logged in using ChatGPT`, reported as app-server account type `chatgpt`.
* `Logged in using an API key`, reported as app-server account type `apiKey`.

The current Codex app-server may return an empty `account` object for an API
Key session while returning `requiresOpenaiAuth=false`. CAG treats that exact
response shape as the API Key mode. Unknown or unauthenticated responses remain
rejected.

`AGENT_GATEWAY_CODEX_REQUIRE_CHATGPT_AUTH=true` remains available for a
ChatGPT-only deployment. The managed host runner sets it to `false` after its
preflight accepts one of the two local Codex login states.

CAG never reads, copies or stores the Codex API Key. The key remains in the
Codex-managed local credential boundary. CAG continues to launch
`codex app-server --stdio` and to use FakeAgentRuntime for deterministic tests.

## Consequences

* Switching the local Codex login mode no longer prevents Gateway startup.
* Runtime events expose only `chatgpt` or `apiKey` as the authentication label.
* A CAG-managed `OPENAI_API_KEY` and direct Responses API integration remain
  outside this decision.
* Deployments that require a ChatGPT-only billing boundary can keep the strict
  flag enabled.

## Verification

The adapter tests cover ChatGPT, explicit API Key, empty-account API Key and
unknown authentication responses. The host app-server account/read handshake
is also checked without starting a model turn.
