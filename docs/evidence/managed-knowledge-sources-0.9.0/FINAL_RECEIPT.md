# Final receipt

Release: 0.9.0

Status: implementation, release tests and runtime acceptance complete. Git
publication is recorded by the enclosing repository history.

Delivered:

* Five maintained source types
* UI and API source location editing with index invalidation
* Operating system credential references
* Git and SVN revision snapshots
* PDF, Office, text, code and script extraction
* Duplicate source and duplicate content controls
* Incremental vector reuse
* Complete ingestion stage SSE
* Independent Knowledge and Memory pages
* API, architecture, security and deployment documentation

Open target-specific acceptance:

* Authenticated UNC share
* Private GitLab repository or Wiki

Rollback:

1. Deploy version 0.8.2.
2. Downgrade Alembic to `20260727_0008`.
3. Remove `AGENT_GATEWAY_KNOWLEDGE_SOURCES_DIR` and file-size settings if no
   longer needed.

Database downgrade removes the new source configuration columns. Operators
must export any required source metadata before downgrade.
