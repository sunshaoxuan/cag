# Stable product knowledge 0.20.0 investigation

## Verified failure

The production Project moved from ProductVersion `0.6.0` to `0.15.0`.
Existing product-scoped chunks retained the earlier ProductVersion. Retrieval
required exact ProductVersion equality, so all completed product chunks were
filtered out before vector and keyword ranking.

The reported SQL sentence was present in a stored chunk. Direct knowledge
search returned no results and the Conversation Task recorded zero citations.

## Implemented correction

Product retrieval now resolves the stable Product physical ID and accepts all
of its ProductVersion records. Tenant retrieval remains exact.

Knowledge documents record their producing ingestion. Existing documents are
backfilled with the latest completed source ingestion. Refresh processing builds
embeddings before the replacement transaction and commits changed documents,
vectors, code facts and the completed receipt together.

A source with completed documents remains approved while refreshing. Refresh
failure preserves the previous generation and records a degraded health state.

The source list now reports actual accessible chunk counts, legacy document
counts and the active completed generation. The management badge follows this
health result.

## Limitations

The release does not automatically start a new ingestion. Legacy SQL remains
searchable immediately and can be upgraded to structural code knowledge through
the existing learning queue after deployment.
