# Test results

## Backend

The complete backend suite collected 125 tests and finished with:

```text
123 passed, 2 skipped, 5 warnings
coverage 85.97%
```

The Codex adapter tests cover ChatGPT authentication, explicit API Key
authentication, the empty-account API Key response, unknown authentication,
ChatGPT-only mode, thread resume, approvals, server requests, event mapping and
invalid JSONL.

## Frontend

The frontend suite finished with 3 test files and 17 passing tests. The
production TypeScript and Vite build completed successfully.

## Host scripts

Pester 3.4.0 ran 10 launcher, supervision and listener checks. All passed,
including the two login status strings, the `0.0.0.0` binding, PostgreSQL and
Redis startup checks, and idempotent managed start.

## Live Agent evidence

The real local Codex app-server task used `read-only-analysis`, returned the
fixed smoke marker, reported `authentication=apiKey` in CAG SSE, and completed
without modifying the workspace.
