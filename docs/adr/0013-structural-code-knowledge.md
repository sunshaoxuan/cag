# ADR 0013: Governed structural code knowledge

## Status

Accepted for version 0.13.0.

## Context

Embedding source files supports semantic retrieval across Japanese, code and
technical documentation. It does not provide stable symbol identity, exact
definition boundaries, call relationships or auditable code-document links.
The Gateway also runs on Windows hosts where application-control policy can
block native parser DLLs.

## Decision

The Gateway stores code structure in `CodeSymbol`, `CodeRelation` and
`CodeDocumentLink`. Each record has an independent UUID physical ID. Strong
references use database foreign keys. Relations and links also carry
deterministic SHA 256 fingerprints and evidence.

Python uses the standard library AST. The Linux image prefetches Tree-sitter
grammars during image build. A language-aware parser handles unsupported files
and native-library failures and records its parser name and diagnostics.

Structure-aware chunks use definition boundaries. Retrieval combines vector,
Japanese n-gram, exact symbol and graph-expansion channels. The deep profile
can use the local `qwen3:14b` model to rerank bounded evidence candidates. Model
output changes ranking only and cannot create structural facts. The reranker
must cover every candidate UUID exactly once and contributes only a Reciprocal
Rank Fusion channel. Invalid or partial output is discarded.

## Consequences

Code investigations can address exact symbols, paths, line ranges, resolved
calls and linked documents. Changed and removed files update dependent facts
through foreign keys, and repeated source ingestion remains idempotent.

The production image build requires one controlled grammar-prefetch step.
Fallback parsing has lower language precision and is visible through parser and
diagnostic fields. Unresolved calls remain explicit rather than being guessed.

## Verification

Backend tests cover Japanese encodings, Python AST, fallback parsing,
symbol-boundary chunks, relation resolution, code-document evidence, deep
reranking, scoped APIs and idempotent reingestion. Alembic tests execute upgrade,
downgrade and re-upgrade. Frontend tests cover the independent route and detail
evidence.

## Rollback

Downgrade Alembic to `20260728_0010`, revert the 0.13.0 release commit and
redeploy 0.12.0. Semantic chunks and vectors remain in the existing knowledge
tables.
