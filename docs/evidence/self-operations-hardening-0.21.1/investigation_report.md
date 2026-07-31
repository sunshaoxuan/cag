# Self-operations production hardening investigation

## Trigger

The 0.21.0 production validation issue `OI-E23F303DCC` ran through the local
ChatGPT-authenticated Codex triage and independent Review path. It stopped at
`waiting_approval` with two artifacts and no implementation branch.

## Findings

The production AI review identified two release-blocking findings:

1. Operations mutation endpoints treated workflow state as the approval gate
   and accepted an administrator name from the request body. They had no
   authenticated administrator principal.
2. Runtime event names ending in `.delta` were persisted with cumulative text.
   One triage and Review cycle created 4,464 events. This creates avoidable
   PostgreSQL growth and transfers the full event array to the management page.

## Correction

Version 0.21.1 requires a configured operations administrator token for
approve, reject, manual and bulk implementation, manual evaluation and reopen
calls. The caller also supplies an administrator identity header. The service
authenticates the token with a constant-time comparison and writes the
header-derived identity to the audit record. Body-provided identities are
ignored.

The operational issue event recorder excludes runtime event names ending in
`.delta`. Completed messages, commands, tests, plans, Reviews, evaluations and
lifecycle events remain durable. Task and Conversation SSE keep their existing
delta contract.

## Isolated browser result

The 0.21.1 management page:

* displayed a password-masked administrator token field;
* retained credentials only across the current browser session;
* rejected a reviewed issue using the authenticated `browser-admin` identity;
* recorded `issue.rejected` with that server-authenticated identity;
* retained 10 bounded timeline events and zero delta events;
* produced zero browser warnings and zero browser errors.
