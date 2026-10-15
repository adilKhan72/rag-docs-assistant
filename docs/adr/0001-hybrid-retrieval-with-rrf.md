# ADR-0001: Hybrid retrieval fused with Reciprocal Rank Fusion

**Status:** Accepted

## Context
Dense (embedding) search is good at paraphrase ("time off" ≈ "annual leave") and bad at exact tokens: policy
numbers, product codes, acronyms, names. Keyword search is the opposite. Real questions mix both.

## Decision
Run both against PostgreSQL in one round-trip: `pgvector` cosine distance (HNSW index) and full-text search
(`websearch_to_tsquery`, a GIN index on a generated `tsvector` column). Fuse the two ranked lists with **Reciprocal
Rank Fusion**: `score(d) = Σ 1 / (k + rank_i(d))`, with `k = 60`.

## Consequences
- RRF uses ranks, not raw scores, so there's no fragile normalisation between cosine similarity and `ts_rank`.
- One database for vectors, text and metadata: transactional ingestion and simple operations. A dedicated vector
  DB becomes worth it only well beyond this scale.
- The weighting is implicit in `k` and the candidate depth per retriever. Both are tuned against the eval set (ADR-0004), not by feel.
