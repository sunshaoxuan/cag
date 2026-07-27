# Paged frontend release receipt

## Release

* Version: 0.7.2
* Date: 2026-07-27
* Scope: CAG frontend information architecture

## Implemented behavior

* `/` provides the overview and three feature-domain entrances.
* `/conversation` contains continuous conversation, Harness controls,
  approvals and the complete SSE event stream.
* `/knowledge` contains knowledge ingestion, vector indexing and memory
  candidate governance.
* `/capabilities` contains capability registration, evaluation, promotion and
  standards controls.
* Navigation uses browser history, supports direct route loading and resets
  scroll position on page changes.

## Verification

| Check | Expected result | Result |
|---|---|---|
| Frontend component and route tests | 7 passing tests | Passed |
| TypeScript and Vite production build | Successful build | Passed |
| Backend regression | Full pytest suite passes | 58 passed, 88.65 percent coverage |
| Docker Compose validation | Valid configuration | Passed |
| Direct route loading | All four routes render their own domain | Passed |
| Browser history | Navigation, back, forward and scroll reset | Passed |
| Browser console | No warnings or errors | Passed, zero warnings and errors |
| Screenshots | Four route screenshots recorded | Passed |

## Rollback

Revert the 0.7.2 release commit and redeploy the 0.7.1 frontend image. The API,
SSE and database contracts are unchanged.
