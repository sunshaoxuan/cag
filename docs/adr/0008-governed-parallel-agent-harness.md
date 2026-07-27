# ADR 0008: Governed parallel Agent Harness

## Status

Accepted for 0.6.0.

## Decision

CAG owns orchestration and starts independent Codex app-server processes for child Agent runs. Investigators receive distinct read-only Git workspaces. Executor is the only writer. Reviews begin after execution. All outputs are stored as versioned, hashed Artifacts and all events enter the parent Task SSE sequence.

Command requests pass through a central policy service. Decisions requiring a person are persisted and can be resolved through the Gateway API.

## Consequences

Parallel investigation can reduce elapsed discovery time while preserving a single writer. Local PostgreSQL is the coordination record. SQLite tests serialize persistence writes while Agent computation remains concurrent.

Task workspace retention remains governed by the deployment cleanup policy. A later release may add worktree pooling after equivalent isolation tests.
