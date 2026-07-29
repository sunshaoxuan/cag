# One Agent Gateway 0.15.0 pgvector runtime investigation

## Scope

This investigation traced the declared database architecture, the active
Windows process, vector storage type, vector ranking path, host launcher,
Compose topology and migration boundary.

## Findings

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| The active 0.12.0 Windows process uses SQLite | Process command line, no PostgreSQL connection, changing `workspaces/.gateway/agent_gateway.db` | High | Active job has not completed |
| The prior Windows launcher created SQLite automatically | Pre-change `scripts/run-local-codex-gateway.ps1` | High | Historical behavior |
| PostgreSQL pgvector already existed in Compose | `docker-compose.yml`, live pgvector 0.8.2 extension | High | Host port was unpublished before 0.15.0 |
| Prior vector ranking ran in Python | Pre-change `KnowledgeService.search()` sorted every candidate with `_cosine` | High | Keyword and graph channels remain application-side |
| 0.15.0 uses native pgvector ranking | `<=>` query implementation and real PostgreSQL integration test | High | Current live 0.12.0 process has not cut over |
| Complete migration is controlled and auditable | Migration source inspection, active-run gate, transactional copy and receipt tests | High | Production-sized source migration waits for the active job |

## Implemented boundary

Version 0.15.0 restricts SQLite to isolated tests and the migration reader.
Managed startup requires PostgreSQL and verifies the vector extension. Health
readiness reports the database backend, native vector-search flag and pgvector
version.

The vector channel executes PostgreSQL cosine ordering and uses the HNSW index.
The migration tool preserves physical IDs and verifies row counts, ID digests,
vector counts and dimensions.

## Live cutover boundary

The active learning process remains unchanged. The migration tool refuses to
run while its ingestion status is `queued` or `running`. After completion, the
operator performs dry run, reviews the receipt, applies the migration and
switches the host database URL.

A live read-only preflight returned `blocked`, SQLite integrity `ok`, ingestion
`6235639f-7ef3-4a9e-b369-b57aa1fce3d0` in `running` state, and 1,875 committed
vectors with dimension 1024. The target database was not contacted.

## Browser verification

An isolated 5174 production frontend confirmed `One Agent Gateway v0.15.0`,
the knowledge-source registry and learning-run center. Connecting it to the
current 0.12.0 backend exposed a missing-field compatibility issue where
`skipped_files` displayed as `undefined`. The frontend now converts missing
legacy counts to zero. Revalidation found no visible `undefined` value.

The selected browser-control surface did not expose console-message capture in
this run. DOM loading, page title, production build, API-backed content and the
saved screenshot were verified. Console-message capture remains an explicit
tooling limitation for this evidence set.
