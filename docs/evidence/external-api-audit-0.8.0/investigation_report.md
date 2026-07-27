# Investigation report

## Question

Can external callers invoke CAG independently of the website, track every
resulting action and observe durable audit data in the UI?

## Verified starting state

`POST /api/v1/tasks` already accepted non-web callers and
`GET /api/v1/tasks/{task_id}/events` exposed one Task SSE. Task events were
durable and included runtime, Harness, knowledge, approval and validation
actions.

The missing controls were caller identity, request identity, idempotency,
Gateway-wide event ordering, cross-task audit querying and a dedicated
monitoring page.

## Implemented chain

```text
External HTTP request
  -> Task admission headers and request hash
  -> client and idempotency lookup
  -> Task and task.created persistence
  -> TaskExecutor, Knowledge, Harness and Codex actions
  -> TaskService.append_event
  -> task sequence plus locked Gateway global sequence
  -> Task SSE plus global audit SSE
  -> Audit APIs and React monitor
```

## Findings

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| Website independence | Real direct HTTP submission returned 202 and a Trace ID | High | Default runner is loopback |
| Complete event boundary | All execution paths persist through `TaskService.append_event` | High | Hidden model reasoning is intentionally excluded |
| Resumable global audit | Automated SSE resume test and real 27-event trace | High | Tamper-evident hash chaining is not implemented |
| Idempotent external call | Automated and real replay returned the original Trace ID | High | Distributed multi-Gateway locking is not released |
| UI monitoring | Browser showed the real external Trace and event 5484 | High | Audit authorization is required before network publication |

## Result

The external API, per-task listener, global listener and monitor are real and
usable on the local Gateway. Cross-machine publication remains gated by caller
authentication, authorization, HTTPS and rate limiting.
