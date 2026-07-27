# Frontend design language

## Scope

Version 0.7.1 restyles the existing CAG frontend. API requests, Conversation
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
| Floating product navigation | Conversation, knowledge and governance anchors |
| Product proof chips | Subscription Codex, 1024-dimensional vectors and full SSE |

## Responsive and accessibility rules

The desktop hero uses two columns and the work console uses paired cards. At
1080 pixels the hero and console collapse to one column. At 760 pixels actions,
proof chips, governance grids and form controls stack. Focus rings use the
turquoise semantic color. Reduced-motion preferences disable transitions and
animations.

## Verification

Required acceptance includes component tests, TypeScript and production build,
the running page at `http://127.0.0.1:5173`, anchor navigation, console
warnings and errors, and a screenshot under `docs/evidence/screenshots`.

Validated screenshots:

* `docs/evidence/screenshots/onehr-design-0.7.1.png`
* `docs/evidence/screenshots/onehr-design-console-0.7.1.png`
