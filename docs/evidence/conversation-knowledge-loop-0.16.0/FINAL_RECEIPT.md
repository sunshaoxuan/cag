# Version 0.16.0 final receipt

## Delivered

* Knowledge-first execution for every assisted Conversation turn
* Resource-linked evidence in Codex app-server developer instructions
* Shared citations across SSE, KnowledgeUsage, final report and memory evidence
* Local, UNC, Git, GitLab and SVN resource URI coverage
* Version, API, architecture, enterprise knowledge, deployment and requirement updates

## Acceptance

Backend, frontend, production build, Docker image and browser checks passed.
The app-server fixture directly verified that resource-linked knowledge reaches
the local Codex protocol boundary.

## Deployment state

Release artifacts are ready. The current long ingestion on port 8000 remains
untouched. Runtime upgrade and PostgreSQL cutover remain gated by that
ingestion reaching a terminal state and the migration receipt passing.

## Rollback

Revert the 0.16.0 release commit. No database schema migration is associated
with this version. Existing JSON citations remain compatible because the new
fields are additive.
