# Frontend design final receipt

## Release

Version 0.7.1.

## Investigation

The current public One人事 homepage was inspected on 2026-07-27 through its
rendered desktop page and public content. The reference uses orange primary
actions, turquoise unified-data semantics, heavy sans-serif headlines, a
floating white navigation bar, connected circular modules and generous white
space.

## Implemented

* Added CAG-owned floating product navigation and anchor links.
* Replaced the editorial green theme with orange action and turquoise data
  semantics.
* Added a responsive integrated task-chain hero using Knowledge, Agent and
  Validator nodes.
* Moved the continuous conversation workspace ahead of governance sections in
  the visual flow.
* Restyled knowledge, capability, conversation, approval and SSE surfaces.
* Preserved all existing API, Conversation, SSE, approval and Harness behavior.
* Added desktop, tablet, narrow-screen, keyboard-focus and reduced-motion rules.

## Evidence

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| Public OneHR language was inspected | `https://onehr.jp/`, rendered 2026-07-27 | high | Public website can change later |
| Existing behavior remains covered | `frontend/src/App.test.tsx` | high | Component tests use mocked HTTP and SSE |
| Production bundle builds | `pnpm run build` | high | Local production build |
| Real page renders current data | `http://127.0.0.1:5173/` browser inspection | high | Local environment |
| Console is clean | Browser warning and error log returned zero entries | high | Checked current desktop tab |
| Visual result is inspectable | `docs/evidence/screenshots/onehr-design-0.7.1.png` and `onehr-design-console-0.7.1.png` | high | Desktop viewport |

## Commands and results

* `pnpm test -- --run`: passed.
* `pnpm run build`: passed.
* `docker compose up -d --build frontend`: frontend rebuilt and healthy.
* Browser anchor navigation from the hero to the conversation workspace:
  passed.
* Browser console warnings and errors: zero.

## Rollback

Revert the 0.7.1 frontend commit, rebuild the frontend image and restore the
0.7.0 version files. Database rollback is not required because this release has
no schema change.
