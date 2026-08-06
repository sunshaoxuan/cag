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
* Use `codex exec --json` only when an explicit current product contract requires that interface.
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

## Mandatory engineering principles

* Do not retain backward compatibility. Delete obsolete implementations, tests, configuration, and documentation directly in the same change. Do not add compatibility layers, migration code, or fallback paths.
* Choose the simplest implementation that satisfies the current requirements. Do not add speculative abstractions or unnecessary configuration layers.
* Build the smallest working end-to-end slice first. Extend the system in layers while keeping the working slice runnable.
* Keep components modular and maintain clear separation of concerns.
* Prefer mature, actively maintained libraries. Reuse existing project dependencies before adding a package or rewriting library behavior. A new package requires a concrete justification.
* Make architecture decisions durable. Record the decision and its consequences in the relevant design documentation. Do not introduce temporary architecture on the assumption that it will be replaced later.
* Research how mature products solve the same problem before designing a new approach. Prefer established, validated patterns over inventing a new pattern without evidence.
* Record requirement changes and architecture changes in the relevant project documentation as part of the same change.

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
