# Phase 1 investigation report

Date: 2026-07-27

Version: 0.1.0

## Question

Determine the authoritative specification, choose the correct local Codex runtime boundary, and establish a verified Phase 1 implementation.

## Findings

### Repository state

The remote repository had no heads and the local repository had no commits. The only initial project artifact was `docs/Agent Gateway 建设任务.docx`. The local unborn branch was renamed from `main` to the required `master`.

### Specification

The DOCX contains 184 paragraphs and no tables. Its first-round task requires architecture, API and security documents, a Phase 1 backend skeleton, database, Fake Runtime, create/query/event APIs, Docker Compose, tests and recorded results.

Structural extraction succeeded. Visual rendering could not be completed because the document omits standard page-size properties and LibreOffice is unavailable in the current environment. No source document edits were made.

### Runtime correction

The intended runtime is the locally installed Codex authenticated through ChatGPT subscription access.

Official Codex documentation confirms:

* ChatGPT sign-in provides subscription access for local Codex clients.
* `codex exec` reuses saved CLI authentication.
* `codex app-server` is the deep integration interface for authentication, conversation history, approvals and streamed events.
* App-server supports stdio JSONL and generated schemas tied to the installed CLI version.

Sources:

* [Codex authentication](https://learn.chatgpt.com/docs/auth)
* [Codex app-server](https://learn.chatgpt.com/docs/app-server)
* [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
* [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk)

### Local runtime evidence

The callable local CLI is:

```text
C:\Users\Administrator\.codex\plugins\.plugin-appserver\codex.exe
```

Verified output:

```text
codex-cli 0.146.0-alpha.3.1
Logged in using ChatGPT
```

The installed CLI exposes `app-server`, stdio transport, schema generation, `exec --json`, output schema, sandbox controls and working-directory controls.

### Phase 1 result

The implementation provides:

* FastAPI service and OpenAPI contract.
* UUID physical IDs and foreign-key relationships.
* PostgreSQL and SQLite persistence.
* Alembic schema revision `20260727_0001`.
* Fake Runtime and background task executor.
* HTTP 202 task creation.
* Task status and structured final report retrieval.
* Ordered SSE events with reconnection sequence.
* Docker Compose for Gateway, PostgreSQL and Redis.

## Evidence table

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| Source scope was extracted | DOCX structural extraction, 184 paragraphs | High | Visual render unavailable |
| ChatGPT subscription is the intended auth boundary | User correction and official authentication docs | High | Subscription limits remain governed by the signed-in account |
| App-server matches the Gateway feature shape | Official app-server docs and local help | High | Adapter implementation is Phase 3 |
| Local Codex is signed in with ChatGPT | `codex login status` output | High | Current host only |
| Phase 1 task lifecycle works | Automated tests and live Compose HTTP smoke | High | Process-local executor is not durable |
| PostgreSQL migration works | Container migration log and Alembic table query | High | Downgrade was covered structurally, not run against the retained Compose volume |

## Remaining scope

Phases 2 through 7 remain open in `docs/requirements-matrix.md`. Production admission remains blocked by authentication, project authorization, workspace isolation, policy, approval, secret scanning, concurrency and audit requirements.
