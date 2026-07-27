# Truthful runtime feedback test results

Date: 2026-07-27

Version: 0.4.0

## Automated validation

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```text
37 passed
Total coverage: 91.45 percent
```

Frontend:

```powershell
cd frontend
pnpm test
pnpm build
```

Result:

```text
5 passed
Production build passed
```

PowerShell management tests:

```text
4 passed
```

Compose configuration:

```text
docker compose config --quiet
Passed
```

## Real local Codex validation

The managed host Gateway used the local ChatGPT-authenticated Codex app-server.
The Compose Fake Runtime remained stopped.

Conversation:

```text
f0d0ef66-c2d2-429d-abcf-129f9393d99a
```

Observed backend ledger:

```text
197 persisted events
188 agent.message.delta events
Conversation sequences 1 through 197
Final cumulative Agent text length 289
```

An SSE reconnect with `Last-Event-ID: 189` returned every event from 190
through 197. The replay included six exact Agent deltas, the final Agent
message and `task.completed`. Each delta carried `item_id`, `turn_id`, the
exact `delta` and cumulative `text`.

## Browser validation

The in-app browser submitted a real prompt through
`http://127.0.0.1:5173/`.

Verified behavior:

* The answer bubble changed during execution and displayed `实时反馈`.
* Standard feedback displayed seven of the first eight backend events.
* Full feedback displayed all fourteen events observed at that checkpoint.
* After completion, the backend count was 197.
* Selecting `全部` rendered 197 event rows.
* Selecting `20 条` rendered the latest 20 event rows.
* The final answer replaced the live projection and ended with
  `TRUTHFUL_FEEDBACK_OK`.
* Browser console errors: zero.
* Full-page screenshot verification: passed in the in-app browser.

## Information boundary

Supported user-visible app-server notifications are persisted and streamed.
Credentials and hidden reasoning remain excluded from the public event
contract.
