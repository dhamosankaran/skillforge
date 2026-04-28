---
slug: hybrid-retrieval
title: Hybrid Retrieval (Lexical + Semantic)
display_order: 0
quiz_items:
  - question: 'On what class of queries does dense retrieval reliably underperform BM25, and why?'
    answer: 'Queries dominated by exact-match tokens — proper nouns, identifiers, version numbers, rare terms — where the embedding model maps near-synonyms to similar vectors but treats unfamiliar tokens as average. BM25 weights rare tokens by IDF, so a query containing a rare identifier ranks documents with that exact token at the top regardless of semantic similarity. This is why product-doc search, code search, and security CVE search all benefit from a BM25 leg even when the dense leg is otherwise dominant.'
    question_type: free_text
    difficulty: medium
    display_order: 0
  - question: 'Implement a weighted-sum fusion that combines normalized BM25 and dense scores into one ranking, with a tunable alpha.'
    answer: |
      def weighted_fuse(
          bm25_scores: dict[str, float],
          dense_scores: dict[str, float],
          alpha: float = 0.6,
      ) -> list[tuple[str, float]]:
          def norm(d: dict[str, float]) -> dict[str, float]:
              if not d:
                  return {}
              lo, hi = min(d.values()), max(d.values())
              span = hi - lo or 1.0
              return {k: (v - lo) / span for k, v in d.items()}
          b, dn = norm(bm25_scores), norm(dense_scores)
          keys = set(b) | set(dn)
          fused = {k: alpha * dn.get(k, 0.0) + (1 - alpha) * b.get(k, 0.0) for k in keys}
          return sorted(fused.items(), key=lambda x: -x[1])
    question_type: code_completion
    difficulty: hard
    display_order: 1
---
## Concept

Hybrid retrieval recognizes that no single similarity function is best
across all query types. Lexical scoring (BM25) wins on exact tokens and
rare terms; dense scoring wins on paraphrases and conceptual queries.
Production retrievers run both and fuse the rankings.

Two fusion strategies dominate:

- **Reciprocal Rank Fusion (RRF).** Score = sum over rankings of
  `1 / (k + rank)`. No per-system score normalization needed.
- **Weighted score fusion.** Normalize each system's scores to [0, 1],
  then weighted-sum with a tunable alpha. More tuning surface, more
  failure modes.

## Production

Two architectural choices to make explicitly:

1. **Single index or two?** Single index (e.g. OpenSearch with both
   bm25 and knn fields) is operationally simpler — one cluster, one
   write path, one consistency story. Two indexes (Postgres + pgvector
   alongside Elastic) allows independent scaling but forces dual-write
   reconciliation.
2. **Where does fusion run?** In-process (cheap, fast) vs in-database
   (some vector stores have native hybrid). In-process gives you
   control over the alpha; in-DB simplifies the wire protocol but
   hides the knobs.

```python
async def hybrid_retrieve(query: str, k: int = 10) -> list[Doc]:
    bm25 = await bm25_search(query, k=100)
    dense = await dense_search(embed(query), k=100)
    fused = rrf([list(bm25.keys()), list(dense.keys())])
    return [DOCS[doc_id] for doc_id in fused[:k]]
```

The default alpha for weighted fusion that holds up across many domains
is around 0.6 (lean dense), but it should be tuned per dataset on a
labeled eval set, not chosen by intuition.

## Examples

| Domain               | Best fusion         | Why                                 |
|----------------------|---------------------|-------------------------------------|
| Code search          | Lean BM25 (α=0.3)   | Identifiers dominate intent         |
| Customer support     | Balanced RRF        | Mix of paraphrase + product names   |
| Legal contracts      | Lean dense (α=0.7)  | Concepts > exact strings            |
| Security advisories  | Lean BM25 (α=0.2)   | CVE IDs and version strings         |

The pattern: pick the fusion strategy by what your queries look like in
production, not by what the demo dataset suggests.
