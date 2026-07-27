# Truthful runtime feedback receipt

Version: 0.4.0

Date: 2026-07-27

Branch: `master`

## Delivered

* Faithful backend mapping for Agent message, plan, command output and
  reasoning-summary notifications.
* Exact Agent message deltas with stable item and turn identity.
* Cumulative Agent text for reconnect-safe live projection.
* Persistent storage and CAG-owned SSE delivery for every supported
  user-visible notification.
* Frontend feedback levels for key, standard and full views.
* Frontend display limits for 20, 50, 100 and all events.
* Live answer projection with authoritative final-answer replacement.
* Architecture, API, requirements and ADR updates.

## Acceptance

Automated backend, frontend, PowerShell and Compose validation: passed.

Real local ChatGPT subscription execution: passed.

SSE resume from event 189 through event 197: passed.

Backend ledger count and frontend count projection: passed.

Browser interaction, console and screenshot checks: passed.

## Rollback

1. Stop the managed local Gateway.
2. Deploy the prior commit.
3. Rebuild only the frontend service without starting its dependencies.
4. Start the managed local Gateway.

No schema rollback is required.
