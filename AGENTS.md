# Agent Gateway repository rules

## Scope

This repository implements the Codex/ChatGPT Agent Gateway described in `docs/Agent Gateway 建设任务.docx`.

## Branch and release policy

* Work only on `master`.
* Do not create feature branches.
* Each version must update `VERSION`, `CHANGELOG.md`, the requirement matrix, and relevant design documents.
* Run all relevant tests before committing.
* Push each verified version directly to `origin/master`.

## Runtime boundary

* Use the locally installed Codex authenticated with ChatGPT subscription access.
* Prefer `codex app-server` for product integration.
* Keep `codex exec --json` as a compatibility runner.
* Do not require or store `OPENAI_API_KEY` for the default runtime.
* Unit and integration tests use `FakeAgentRuntime` and must not consume external model quota.

## Engineering conventions

* Python code targets Python 3.12.
* Business and archive records use independent UUID physical IDs.
* Business codes are display and lookup identifiers. Strong references store physical IDs with database foreign keys.
* All shell execution must pass through the command policy service once that phase is implemented.
* Secrets must stay outside Git, prompts, task logs, and plaintext database fields.
* Every implemented behavior needs tests and documentation.
* Do not claim a planned module is implemented.

## Required verification

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Before a release commit:

```powershell
git diff --check
git status --short
```
