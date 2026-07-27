# Frontend design language

## Scope

Version 0.7.2 restyles and separates the existing CAG frontend. API requests, Conversation
state, SSE event handling, approval actions, Harness controls, knowledge
operations and capability governance keep their existing contracts.

## Reference

The visual investigation used the public One人事 website at
`https://onehr.jp/` on 2026-07-27. CAG adopts the design language and does not
copy the One人事 logo, photography, illustrations or product claims.

## Extracted rules

* Saturated orange is the primary action and headline accent.
* Turquoise communicates unified data, healthy runtime state and connected
  workflow.
* Primary headings use a heavy sans-serif face with tight tracking.
* A floating white navigation surface remains visible while scrolling.
* Large white space and softly tinted geometric backgrounds separate major
  sections.
* Circular nodes present related modules as one connected workflow.
* Primary and secondary actions use filled and outlined rounded rectangles.
* Content areas use white cards, restrained shadows and clear section numbers.

## CAG mapping

| OneHR visual concept | CAG application |
|---|---|
| OneDB integrated modules | Knowledge, Agent and Validator task chain |
| Orange commercial action | Start task, send, approve and index actions |
| Turquoise data layer | Knowledge vectors, SSE and completed runtime state |
| Floating product navigation | Overview, conversation, knowledge and governance routes |
| Product proof chips | Subscription Codex, 1024-dimensional vectors and full SSE |

## Routed information architecture

| Route | Responsibility |
|---|---|
| `/` | Product overview, runtime proof and links to the three operational domains |
| `/conversation` | Continuous conversation, Harness configuration, approvals and the complete CAG SSE event stream |
| `/audit` | External API call traces and the resumable Gateway-wide audit SSE |
| `/knowledge` | Knowledge source ingestion, idempotent vector indexing and governed memory candidates |
| `/capabilities` | Skill, Tool, Validator, promotion and standards control governance |

The conversation route is an API test console. It marks task submissions as
`test_console`; external callers default to `external_api`. Route transitions
use browser history and reset document scroll position. Direct
loads and reloads are served by the frontend fallback. Conversation state stays
mounted during in-app navigation so an active task remains observable.

## Responsive and accessibility rules

The desktop hero uses two columns and the work console uses paired cards. At
1080 pixels the hero and console collapse to one column. At 760 pixels actions,
proof chips, governance grids and form controls stack. Focus rings use the
turquoise semantic color. Reduced-motion preferences disable transitions and
animations.

## Verification

Required acceptance includes component and route tests, TypeScript and
production build, direct loading of all four routes at
`http://127.0.0.1:5173`, browser history navigation, console warnings and
errors, and screenshots under `docs/evidence/screenshots`.

Validated screenshots:

* `docs/evidence/screenshots/onehr-design-0.7.1.png`
* `docs/evidence/screenshots/onehr-design-console-0.7.1.png`
* `docs/evidence/screenshots/paged-overview-0.7.2.png`
* `docs/evidence/screenshots/paged-conversation-0.7.2.png`
* `docs/evidence/screenshots/paged-knowledge-0.7.2.png`
* `docs/evidence/screenshots/paged-capabilities-0.7.2.png`
