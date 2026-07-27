# ADR 0009: Governed self learning in the Gateway

## Status

Accepted for 0.7.0.

## Context

Engineering experience must remain an enterprise asset and must be reusable
across tasks without exposing customer knowledge or allowing an Agent to
rewrite its own authority.

## Decision

CAG owns a versioned capability registry for Skill, Tool, Validator, Harness
Profile and Memory assets. Agents and the knowledge curator may create
proposals. Only the Promotion Service may advance an asset through validated,
benchmarked, shadow, canary and active states.

An active asset applies to the current Agent Gateway deployment. Activation
does not write to Codex installation directories, formal AGENTS.md files or
another Gateway.

Every asset is content addressed. Every active promotion and rollback creates
an external installation receipt containing source, version, hash, scope,
evidence, validation and rollback data.

## Consequences

Learning is durable and measurable. Promotion latency is intentionally longer
because 20 replay cases, two project contexts, ten shadow runs and five canary
runs are mandatory. Security, architecture, success rate and quality gates
cannot be bypassed by a task prompt.
