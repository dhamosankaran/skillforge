---
slug: retrieval-and-ranking
title: Retrieval and Ranking for RAG
display_order: 1
quiz_items:
  - question: 'Why is dense vector similarity alone usually insufficient for production retrieval, and what is the standard mitigation?'
    answer: 'Dense embeddings capture semantic similarity but miss exact-token matches (proper nouns, IDs, rare terms) and are blind to question intent vs document type. The standard mitigation is hybrid retrieval — combine BM25 (lexical) and dense (semantic) scores, then rerank the union with a cross-encoder so query and candidate are scored jointly rather than independently.'
    question_type: free_text
    difficulty: medium
    display_order: 0
  - question: 'Implement a Reciprocal Rank Fusion combiner that merges BM25 and dense rankings into a single ordered list.'
    answer: |
      def rrf(rankings: list[list[str]], k: int = 60) -> list[str]:
          scores: dict[str, float] = {}
          for ranking in rankings:
              for rank, doc_id in enumerate(ranking):
                  scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
          return [doc_id for doc_id, _ in sorted(scores.items(), key=lambda x: -x[1])]
    question_type: code_completion
    difficulty: hard
    display_order: 1
---
## Concept

A retriever's job is to put the right context in the LLM's hands. Two
properties matter: recall (the relevant chunk is in the top-K) and
precision (the top-K isn't dominated by near-misses). Pure dense
retrieval optimizes semantic similarity but loses on exact-match
queries — IDs, function names, proper nouns. Pure lexical (BM25) loses
on paraphrases.

Production systems use hybrid retrieval: BM25 for lexical recall, dense
for semantic recall, then rerank the union with a cross-encoder that
scores (query, candidate) jointly.

## Production

The minimal hybrid pipeline:

```python
bm25_hits = bm25.search(query, k=100)
dense_hits = vector_db.search(embed(query), k=100)
fused = rrf([bm25_hits, dense_hits])
reranked = cross_encoder.rerank(query, fused[:50])[:10]
```

Tune the candidate pool size at each stage: too small at the retrieval
stage and recall caves; too large at the rerank stage and latency
balloons. A rerank cross-encoder like `bge-reranker-v2-m3` or
`mxbai-rerank-large` is 100x slower per pair than dense scoring but
gives massively better top-K ordering.

## Examples

| Stage           | Tool                   | Top-K | Latency budget |
|-----------------|------------------------|-------|----------------|
| BM25            | OpenSearch / Elastic   | 100   | <50 ms         |
| Dense           | pgvector / Pinecone    | 100   | <80 ms         |
| RRF fuse        | in-process             | 50    | <5 ms          |
| Cross-encoder   | bge-reranker-v2-m3     | 10    | <300 ms        |

If your end-to-end retrieval budget is 500 ms, the cross-encoder rerank
is your largest line item — batching candidates is the obvious win.
