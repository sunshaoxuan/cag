# Managed knowledge sources investigation

## Scope

Repository root: `D:\workspace\cag`

Branch: `master`

Requested boundary: maintain local directories, authenticated network shares,
Git, GitLab and SVN sources from CAG; trigger collection, cleaning, indexing and
memory persistence; preserve idempotency.

## Existing facts

The 0.8.2 knowledge service accepted only an authorized host directory.
KnowledgeDocument already had source plus canonical path uniqueness.
KnowledgeChunk already had document plus ordinal uniqueness. Repeated ingestion
compared content hashes and reused unchanged vectors.

The missing boundary was source connection, remote revision materialization,
write-only source credential handling, duplicate source registration, duplicate
content inside a snapshot and a maintenance UI.

## Implemented trace

```text
Knowledge page form
  |
POST source configuration
  |
opaque credential reference
  |
validate connector
  |
materialize revision or open selected directory
  |
extract supported documents
  |
normalize, secret scan and Prompt Injection scan
  |
content hash deduplication
  |
incremental path and hash comparison
  |
Ollama embedding
  |
encrypted Source Memory and pgvector
  |
durable ingestion SSE
```

GitLab project repositories and Wiki Git repositories use the Git connector.
SVN credentials enter the process through standard input. Authenticated UNC
shares use the Windows WNet API. No source secret is returned by the API.

## Runtime evidence

The browser registered `D:\workspace\cag` with subpath `docs/adr`, validated
the source and ran two real ingestions against local Ollama.

First run:

* 10 files seen
* 11 chunks written
* 0 rejected files
* 0 duplicate files

Second run:

* 10 files seen
* 0 chunks written
* 10 unchanged files
* 11 vectors reused
* identical index fingerprint

The browser displayed all ten durable ingestion stages. Console warning and
error count was zero.

## Acceptance boundary

Real local directory, local Git and local SVN behavior was executed. The host
reported `WinVaultKeyring` and Ollama readiness. No authenticated UNC share or
private GitLab credential was supplied for live acceptance. Those two paths are
covered by connector contracts and remain deployment-target acceptance items.

OCR, GitLab issues, merge requests and package registries are outside this
release. GitLab repository files and Git-backed Wiki files are supported.
