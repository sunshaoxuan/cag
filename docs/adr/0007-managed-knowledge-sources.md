# ADR 0007: Managed multi-protocol knowledge sources

## Status

Accepted

## Context

Enterprise knowledge can live in host directories, authenticated file shares,
GitLab, Git and SVN. Indexing a remote working location directly would make a
run difficult to reproduce and could expose credentials through command
arguments or logs.

## Decision

CAG owns a source registry and connector boundary. Git and SVN inputs are
materialized into revision-addressed managed snapshots. Local and UNC
directories are read through a selected root and optional safe subpath. All
connectors feed one extractor, cleaning, content hash, embedding and encrypted
Source Memory pipeline.

Secrets use the operating system credential store. Git uses an environment
authorization header. SVN uses password input on stdin and disables its auth
cache. Authenticated UNC access uses the Windows WNet API.

Source identity is content addressed by type, normalized location, reference,
subpath and governance scope. File content is deduplicated before chunking.
Existing path and content hash records provide incremental vector reuse.

## Consequences

Collection can be replayed and audited by source revision. Source secrets stay
outside the database and events. Immutable snapshots require a retention
policy for long-running deployments. OCR, GitLab issues, merge requests and
package registries remain separate future connectors.

## Rollback

Downgrade the database to `20260727_0008`, remove the managed source settings
and deploy the prior application version. Deleting a source through the API
removes its credential reference, indexed records and managed snapshot cache.
