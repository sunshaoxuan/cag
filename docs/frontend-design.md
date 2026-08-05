# Frontend design language

## Scope

Version 0.14.0 keeps the OneHR language and separates the CAG frontend. API requests, Conversation
state, SSE event handling, approval actions, Harness controls, knowledge
operations and capability governance keep their existing contracts.

Starting with version 0.14.0, the persistent header uses the product name
`One Agent Gateway` and renders the packaged frontend version immediately
after it in smaller type. The version value comes from
`frontend/package.json`.

The enterprise knowledge route begins with a lifecycle management surface.
Operators can search and filter registered sources, open the create or edit
form only when needed, validate, enable, disable and trigger learning from each
source. A continuously visible learning run center shows the active source,
status, start time, directory, file progress, rejected count and skipped count.
Run history remains attached to each source and opens its file-level rejection
audit.

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
| Product proof chips | Local Codex Agent runtime, 1024-dimensional vectors and full SSE |

## Routed information architecture

| Route | Responsibility |
|---|---|
| `/` | Product overview, runtime proof and links to the three operational domains |
| `/conversation` | Continuous conversation, Harness configuration, approvals and the complete CAG SSE event stream |
| `/audit` | External API call traces and the resumable Gateway-wide audit SSE |
| `/knowledge` | Managed local, network, Git, GitLab and SVN sources with live collection SSE |
| `/code-knowledge` | Code symbols, relationships, parser evidence and linked documentation |
| `/memory` | Governed task memory candidates and product-level promotion |
| `/operations` | Operational issue decisions, self-improvement approval, revision, no-modification closure and audit evidence |
| `/api-docs` | Online API contracts and copyable integration examples |
| `/capabilities` | Skill, Tool, Validator, promotion and standards control governance |

Port 5173 is the unified CAG visual management console. The overview, API
monitor, enterprise knowledge and capability routes provide management
functions. The conversation route is an API test console. It marks task
submissions as `test_console`; external callers default to `external_api`.
Route transitions
use browser history and reset document scroll position. Direct
loads and reloads are served by the frontend fallback. Conversation state stays
mounted during in-app navigation so an active task remains observable.

Starting with version 0.19.0, the conversation route separates execution
feedback from the terminal answer. Agent messages remain truthful SSE records
and are grouped by Agent run and message item in a gray disclosure that is
collapsed by default. The chat answer is populated from `final_report.summary`
only after `task.completed`. Terminal reports render GitHub-flavored Markdown,
including headings, lists, links, code, blockquotes and tables. The adjacent
event monitor continues to expose the complete filtered or unfiltered event
sequence.

The Knowledge route uses an editable source registry form followed by source
cards and a live ingestion event panel. Location, type, version, subpath,
scope, sync policy and credentials can be maintained from the page. Credential
inputs load the saved value from Windows Credential Manager only after the user
enters source editing. The password field remains masked initially and provides
display, hide and copy actions. The UI reports scheduler state, next check, latest
content change, failure count, files seen, changed and removed paths, and reused
vectors. Each source expands its latest fifty persisted synchronization runs.
The page refreshes source state every ten seconds while visible. Source Memory
and task-derived Memory Candidates remain separate concepts and use separate
routes.

The ingestion panel automatically follows a queued or running scheduled
ingestion. Directory progress is rendered as human-readable current-directory,
scanned-directory, pending-directory and file counts. The browser can display
the latest 50, 100 or 200 events. Its in-memory projection retains at most 200
events and tracks the complete received count separately, while the Gateway
persists and serves the complete sequence.

The Memory route uses the same 30 pixel panel gutter as the Knowledge and
Capability routes. Its empty state stays inside a bordered inner surface so
headings, governance labels and status text share one alignment grid.

The Code Knowledge route remains separate from source maintenance. Its summary
shows symbol, relationship, document-link and unresolved-relation counts. The
left pane filters physical code symbols by project, name, qualified name, path
and kind. The right pane shows signature, line range, parser, calls, dependency
resolution status and deterministic documentation evidence. Long symbol lists
scroll inside the pane, keeping the selected evidence visible.
The code search action uses the same control height as its project, query and
kind fields, keeping the action aligned with the control row. At the mobile
stacking breakpoint, the action remains a full-width row item without an extra
alignment offset.

The production frontend uses its own origin for API and SSE requests. Nginx
forwards `/api` to the host Gateway, so a browser opened through a LAN IP does
not resolve the Gateway as the browser machine's loopback address.

Starting with version 0.22.5, the Operations route places one administrator
decision panel immediately below the issue title. It remains present for every
issue status. Occurrence count is shown as impact context and never hides
authority. The panel presents only server-authoritative actions: approve an
approval-ready self-improvement plan, request a new plan and Review, record
external implementation evidence, reject the current cycle with an explicit
no-modification decision, or explain that an active AI or evaluation step must
finish first.

## Responsive and accessibility rules

The Knowledge source file inventory provides source-scoped relative-path
search, clear, previous and next controls. Each page requests 100 rows from the
existing source entry endpoint and preserves the active query while paging.
The table exposes processing mode, status, extractor identity, processed time
and last-seen time. A failed request remains inside the source inventory and
keeps the entered query available for retry.

The desktop hero uses two columns and the work console uses paired cards. At
1080 pixels the hero and console collapse to one column. At 760 pixels actions,
proof chips, governance grids and form controls stack. Focus rings use the
turquoise semantic color. Reduced-motion preferences disable transitions and
animations.

## Verification

Required acceptance includes component and route tests, TypeScript and
production build, direct loading of all seven routes at
`http://127.0.0.1:5173`, browser history navigation, console warnings and
errors, and screenshots under `docs/evidence/screenshots`.

Validated screenshots:

* `docs/evidence/screenshots/onehr-design-0.7.1.png`
* `docs/evidence/screenshots/onehr-design-console-0.7.1.png`
* `docs/evidence/screenshots/paged-overview-0.7.2.png`
* `docs/evidence/screenshots/paged-conversation-0.7.2.png`
* `docs/evidence/screenshots/paged-knowledge-0.7.2.png`
* `docs/evidence/screenshots/paged-capabilities-0.7.2.png`
* `docs/evidence/screenshots/managed-knowledge-sources-0.9.0.png`
* `docs/evidence/screenshots/managed-knowledge-ingestion-0.9.0.png`
* `docs/evidence/screenshots/managed-knowledge-source-edit-0.9.0.jpg`
* `docs/evidence/screenshots/memory-panel-spacing-0.9.1.jpg`
* `docs/evidence/screenshots/durable-knowledge-sources-0.10.0.jpg`
* `docs/evidence/screenshots/credential-reveal-0.11.0.jpg`
* `docs/evidence/screenshots/directory-progress-0.12.0.jpg`
* `docs/evidence/screenshots/code-knowledge-overview-0.13.0.png`
* `docs/evidence/screenshots/code-knowledge-0.13.0.png`
* `docs/evidence/screenshots/knowledge-source-management-0.14.0.jpg`
* `docs/evidence/screenshots/knowledge-rejection-audit-0.14.0.jpg`
