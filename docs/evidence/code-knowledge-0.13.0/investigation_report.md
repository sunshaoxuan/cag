# Structural code knowledge investigation

## Question

Which capabilities remain insufficient when `qwen3-embedding:8b` is used for a
Japanese enterprise knowledge base that must understand code and connect code
to documentation?

## Evidence chain

1. The existing extractor decoded text as UTF-8 only.
2. The existing chunker used fixed character windows.
3. The database contained documents and chunks without code symbols,
   relationships or code-document links.
4. Retrieval combined vector similarity and whitespace keyword matching.
5. Japanese queries do not consistently contain spaces.
6. Embeddings can rank semantic similarity but cannot provide stable symbol
   identity, foreign-key relationships or deterministic source locations.
7. The Windows host blocks the Tree-sitter native DLL through application
   control policy.
8. The Linux package provides downloadable grammar manifests and works inside
   the Gateway image.

## Conclusion

The embedding model remains the semantic layer. CAG now owns the missing
structural layer: Japanese encoding detection, parser facts, symbol-boundary
chunks, code relationships, deterministic code-document links, Japanese
keyword recall, symbol recall, graph expansion and local deep reranking.

Structural facts come only from parsers and deterministic evidence. Ollama
changes ranking and generates memory candidates. Codex remains the engineering
reasoning and tool-execution runtime.

## Scope boundary

The release does not claim complete static analysis for every language. Native
Tree-sitter and Python AST provide higher precision. The fallback parser and
unresolved relationship records make degraded precision visible.
