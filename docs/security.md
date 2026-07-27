# Agent Gateway Security

## 1. Trust boundary

The Gateway is the only network-facing control plane. The local Codex runtime stays behind it as a child process or loopback-only app-server.

Version 0.6.0 is a local enterprise knowledge and governed Harness foundation. Its public APIs remain limited to trusted loopback or isolated networks until authentication and project authorization are released.

## 2. Codex subscription credentials

The runtime reuses the locally saved Codex CLI session created by `codex login` with ChatGPT.

Rules:

* The Gateway checks only whether Codex reports an authenticated state.
* Phase 3 requires app-server `account/read` to report account type `chatgpt`.
* The Gateway does not open or parse `auth.json`.
* The Gateway does not copy credential files into task workspaces or containers.
* Credential contents never enter prompts, logs, events, artifacts or database rows.
* Codex app-server is started locally and is not exposed directly to untrusted networks.
* A remote app-server listener requires TLS and transport authentication.
* `OPENAI_API_KEY` is neither read nor accepted as the Phase 3 authentication boundary.

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

Enterprise knowledge text is scanned before persistence and encrypted with AES GCM. The data key is obtained from Windows Credential Manager or an explicitly configured server secret. Search vectors and keyword projections contain derived information and still require encrypted host storage.

Knowledge source text is untrusted input. Prompt Injection markers exclude suspicious chunks from Codex context. Injected blocks carry explicit source IDs, paths, scopes and immutable source commits.

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

Harness roles apply a permission intersection. Investigators and reviewers use read-only app-server sandboxes. Executor receives workspace-write. Approval callbacks pass through Command Policy Engine and persistent ApprovalRequest records. Unknown commands wait for an explicit decision until the configured timeout.

## 7. Workspace isolation

Each writing task receives its own Git clone or worktree. The executor prevents two writing tasks from sharing one Git working directory. Task processes receive explicit filesystem roots and resource limits.

Phase 2 implements one Git clone per task under the configured workspace root and keeps the host filesystem path out of API responses. Runtime sandbox enforcement, resource limits, cleanup policy, URL allowlisting and credential-safe private repository cloning remain production gates.

## 8. Network and service exposure

* PostgreSQL and Redis have no host ports in the default Compose file.
* Gateway exposes port 8000 for development.
* Frontend exposes port 5173 for development.
* Codex app-server uses stdio by default.
* Loopback WebSocket mode is reserved for controlled local integration.
* Non-loopback app-server WebSocket mode is excluded until its experimental support and authentication constraints are explicitly accepted.

## 9. Self-improvement boundary

The `self-improvement-candidate` profile grants write access to one task-specific candidate directory. It does not grant write access to installed user Skills, project rules or validators.

Runtime Profile names are validated against each Project YAML allowlist. Formal installation requires a future approval service, evaluation evidence, an installation receipt and rollback instructions.

## 10. Current limitations

The ChatGPT-authenticated local Codex runtime, persistent Conversations, CAG SSE, restricted candidate path and knowledge ingestion Secret Scanner are implemented. Identity authentication, authorization, complete command policy enforcement, approval persistence, durable queueing and audit immutability remain open in the requirement matrix.

## 11. Capability promotion security

Capability definitions pass schema, dependency, permission, supply chain,
Secret Scanner and sensitive identifier checks before benchmark promotion.
Security and architecture test pass rates must both equal 100 percent.

Agents can propose assets and record evidence. Only the Promotion Service can
advance state or activate a capability. Effective permissions remain the
intersection of project policy, Harness Profile, capability declaration and
Command Policy Engine.

Two consecutive rollout failures or a rolling quality decrease beyond five
percent returns the asset to benchmarked status. Active state and canary
counters are cleared. Installation and rollback receipts are stored outside
the project repository when the self improvement root is configured.
