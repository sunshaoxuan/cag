# ADR 0003: Project registry and task workspaces

Status: Accepted

Date: 2026-07-27

## Context

The Gateway must resolve a business project reference into durable repository settings and must prevent concurrent writing tasks from sharing one working directory.

Project Code and name can change. Strong references therefore require an independent stable physical ID.

## Decision

Project configuration lives in versioned `projects/*.yaml` files. Every definition contains:

* Stable UUID `physical_id`.
* Business `id` used as Project Code.
* Repository URL and default branch.
* Workspace type.
* Instruction files.
* Default and allowed runtime profiles.

The registry accepts either the UUID or Code at the API boundary. Project, Task and related database references store the UUID.

Every task receives a Git clone at:

```text
workspaces/{project_physical_id}/{task_id}
```

The manager clones only the configured default branch, resolves `HEAD`, stores the commit SHA, and passes the workspace path directly to the runtime. API responses expose the logical workspace ID and commit SHA while withholding the host path.

## Consequences

* Concurrent tasks do not write into the same Git directory.
* A task records the repository state from which it started.
* YAML changes remain reviewable through Git history.
* Clone cost is paid for every task.
* Private repository credential handling, repository allowlisting, cleanup and resource quotas remain future production gates.

## Rollback

Disable task admission, retain task records and named volumes for audit, revert the release commit, and apply the Alembic downgrade only after an explicit data-retention decision.
