# Current release test results

Date: 2026-07-27

Version: 0.4.0

## Automated

| Check | Result |
|---|---|
| Backend Pytest | 36 passed |
| Backend coverage | 91.06 percent |
| Frontend Vitest | 3 passed |
| Frontend production build | Passed |
| Compose configuration | Passed |
| Gateway image build | Passed |
| Frontend image build | Passed |

## Live local subscription

One CAG Conversation completed two local ChatGPT-authenticated Codex Tasks in distinct Git workspaces. The first turn stored marker `CAG-PERSIST-7F3A91`; the second turn resumed the same internal Codex thread and returned the exact marker.

Conversation SSE IDs were continuous from 1 through 16. Resume after cursor 8 returned IDs 9 through 16.

## Self-improvement

The scoped candidate Task wrote `CANDIDATE.md` and `TASK_LEARNING_RECEIPT.md` only under its assigned `D:\workspace\codex-selfimp\outputs\cag-{task_id}` directory. The project workspace remained clean and the receipt status is `proposed`.

## Container and browser

All four Compose services are healthy. PostgreSQL is at Alembic revision `20260727_0004`. The browser completed two turns through one Conversation and rendered event IDs 1 through 16. Console warnings and errors were zero.

Screenshot:

```text
docs/evidence/screenshots/phase4-continuous-conversation.png
```
