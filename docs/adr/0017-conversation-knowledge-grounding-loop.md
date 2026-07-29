# ADR 0017: Conversation knowledge grounding loop

Status: Accepted

Date: 2026-07-29

## Context

Conversation SSE already owns multi-turn event continuity and Codex thread
reuse. Governed retrieval already ran before runtime execution and injected
bounded knowledge fragments. The injected block exposed a canonical relative
path and source commit. It did not expose a resource URI, the final report did
not retain the citations, and MemoryCandidate evidence referenced only the
Task.

This left the source, Codex analysis, answer and learned memory connected by
separate records instead of one explicit grounding chain.

## Decision

Every Conversation Task keeps `knowledge_mode=assist` as its default. The
Gateway completes authorized retrieval before starting or resuming the Codex
app-server turn.

Each selected evidence block contains:

* chunk physical ID
* source physical ID, name and type
* canonical source-relative path
* source commit or revision
* source-specific resource URI
* bounded plaintext evidence

Local and UNC sources use file URIs. GitLab and recognized Git web origins use
revision-pinned links. Other repository types retain their original repository
URI together with revision and path.

Codex developer instructions require learned evidence to be analyzed first,
allow original-resource lookup through the URI when more context is needed,
and request relevant URI citations in the answer.

The citation object is reused across KnowledgeUsage, SSE context-injection
events, Task final reports and MemoryCandidate evidence. Knowledge plaintext
remains excluded from SSE and audit payloads.

## Security boundary

Tenant and ProductVersion authorization, source approval, prompt-injection
exclusion and context limits run before context construction. URI generation
does not add credentials. Repository source validation already rejects
userinfo credentials in locations.

## Consequences

Conversation answers have a deterministic evidence handoff to Codex and a
traceable source chain after completion. Resource URI formats remain dependent
on source type. A generic repository link can require Codex to use its revision
and path metadata instead of direct browser navigation.

## Rollback

Revert the 0.16.0 release commit. Existing stored citations without
`resource_uri` remain readable because the new fields are JSON metadata and no
database migration is required.
