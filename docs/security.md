# Agent Gateway Security

## 1. Trust boundary

The Gateway is the only network-facing control plane. The local Codex runtime stays behind it as a child process or loopback-only app-server.

Phase 1 is a development foundation. Its public Task API has no production authentication and must only bind to trusted local or isolated networks. Authentication and project authorization are required before any shared deployment.

## 2. Codex subscription credentials

The runtime reuses the locally saved Codex CLI session created by `codex login` with ChatGPT.

Rules:

* The Gateway checks only whether Codex reports an authenticated state.
* The Gateway does not open or parse `auth.json`.
* The Gateway does not copy credential files into task workspaces or containers.
* Credential contents never enter prompts, logs, events, artifacts or database rows.
* Codex app-server is started locally and is not exposed directly to untrusted networks.
* A remote app-server listener requires TLS and transport authentication.

## 3. Secrets

Secrets may exist only in server-side environment variables, the operating system credential store, or a supported Secret Manager.

Forbidden locations:

* Frontend bundles.
* Git.
* Task prompts.
* Task logs.
* Plaintext database fields.
* Agent workspaces.

Output and artifacts will pass through a Secret Scanner before persistence or delivery.

## 4. Authorization model

Planned permissions:

```text
read
workspace_write
shell_safe
shell_privileged
network_access
database_read
database_write
git_commit
git_push
create_merge_request
deploy_test
deploy_production
skill_propose
skill_merge
```

Project membership and runtime profile permissions combine by intersection. No profile may expand a user's permissions.

## 5. Command policy

All shell commands will pass through a Policy Engine and be classified as:

```text
safe
approval_required
forbidden
```

The policy is configuration and code, independent of Prompt instructions.

## 6. Approval policy

High-risk actions create a durable approval request and suspend the task. Approval resolution is audited and resumes only the pending action.

Protected branch push and production deployment remain forbidden defaults. Project administrators may define stricter policies.

## 7. Workspace isolation

Each writing task receives its own Git clone or worktree. The executor prevents two writing tasks from sharing one Git working directory. Task processes receive explicit filesystem roots and resource limits.

## 8. Network and service exposure

* PostgreSQL and Redis have no host ports in the default Compose file.
* Gateway exposes port 8000 for development.
* Codex app-server uses stdio by default.
* Loopback WebSocket mode is reserved for controlled local integration.
* Non-loopback app-server WebSocket mode is excluded until its experimental support and authentication constraints are explicitly accepted.

## 9. Phase 1 limitations

Phase 1 provides data integrity, deterministic runtime tests and private container services. It does not yet provide identity authentication, authorization, rate limiting, command policy enforcement, isolated Git workspaces, Secret Scanner, approval persistence or audit immutability. Those items remain open in the requirement matrix.
