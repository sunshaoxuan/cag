# Test results

## Automated

| Check | Result |
|---|---|
| Backend pytest | 108 passed, 2 skipped, 85.66 percent coverage |
| Frontend Vitest | 13 passed |
| TypeScript and Vite build | Passed, 267 modules transformed |
| Production dependency audit | No known vulnerabilities |

The frontend test renders a Markdown heading, strong text, list, GFM table
and link from `final_report.summary`. It also verifies that an Agent delta is
stored in a `details.message-intermediate` element without the `open`
attribute.

## Isolated browser

| Check | Result |
|---|---|
| Packaged version label | `v0.19.0` |
| Intermediate disclosure count | 1 |
| Default disclosure state | `open=false` |
| Computed text color | `rgb(116, 121, 125)` |
| Computed background | `rgb(244, 245, 246)` |
| Final result region | Present after terminal Task state |
| Console errors or warnings | 0 |
| Screenshot | `docs/evidence/screenshots/conversation-message-presentation-0.19.0.png` |

The first disposable SQLite acceptance run used two interactive workers and
showed SQLite's lack of PostgreSQL row-claim semantics. The final acceptance
run used one isolated worker, produced one Task execution and completed
cleanly. Production PostgreSQL queue behavior was not changed by this UI
release.

## Production release gate

The live health endpoint reported version 0.18.0. Two knowledge ingestions
were non-terminal, with one running and one queued. No production process was
restarted and no production port was modified.
