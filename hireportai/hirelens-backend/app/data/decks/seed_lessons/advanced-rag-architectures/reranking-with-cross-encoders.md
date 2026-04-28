---
slug: reranking-with-cross-encoders
title: Reranking with Cross-Encoders
display_order: 1
quiz_items:
  - question: 'Why does a cross-encoder reranker produce better top-K ordering than a bi-encoder retriever, despite both using the same underlying transformer family?'
    answer: 'A bi-encoder embeds the query and the document independently and scores them via cosine similarity — the document''s representation never sees the query. A cross-encoder concatenates [query, document] into a single forward pass, so attention layers can compare token-to-token between query and candidate. The result is a much sharper relevance score at the cost of being O(N) per (query, candidate) pair instead of O(1) lookups, which is why cross-encoders only run on the top-K candidates from a cheaper retriever.'
    question_type: free_text
    difficulty: medium
    display_order: 0
  - question: 'A team rerank latency budget is 200ms for 50 candidates against a 7B-param cross-encoder. Which option is the most defensible architectural choice?'
    answer: 'Run a smaller distilled cross-encoder (e.g. bge-reranker-base, ~280MB) and let the latency budget cover the full top-50; reserve the 7B model for an offline eval-only path.'
    question_type: mcq
    distractors:
      - 'Use the 7B model and cut the candidate pool to top-5'
      - 'Use the 7B model and parallelize across 50 GPUs'
      - 'Skip the cross-encoder and trust the bi-encoder ranking'
    difficulty: hard
    display_order: 1
---
## Concept

A cross-encoder is a transformer that takes `[CLS] query [SEP]
document [SEP]` as a single input and outputs a relevance score. Unlike
a bi-encoder (which embeds query and document separately and compares
the embeddings), the cross-encoder lets attention range across both
texts, producing a much higher-fidelity score.

The cost: O(N) forward passes per query, vs O(1) embedding lookup. So
cross-encoders only run on a candidate pool from a cheaper retriever
(BM25, dense, or hybrid).

## Production

The reranker pipeline:

1. **Cheap retrieval.** BM25 + dense, fused. Pull top-100.
2. **Cross-encoder rerank.** Score each (query, candidate) pair. Sort.
3. **Top-K to LLM.** Pass the top 5-10 to the generator.

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")

def rerank(query: str, candidates: list[str], k: int = 10) -> list[str]:
    pairs = [[query, c] for c in candidates]
    scores = reranker.predict(pairs, batch_size=32)
    ranked = sorted(zip(candidates, scores), key=lambda x: -x[1])
    return [c for c, _ in ranked[:k]]
```

Latency budget realities at 50 candidates:

- bge-reranker-base on CPU: 1500-3000ms (too slow for online).
- bge-reranker-base on T4: 80-150ms (workable).
- bge-reranker-v2-m3 on A10: 200-400ms (high quality).
- 7B reranker on A100: 1-3s (offline only).

## Examples

| Reranker model           | Size  | T4 50-cand latency |
|--------------------------|-------|---------------------|
| bge-reranker-base        | 280MB | ~120ms              |
| bge-reranker-large       | 560MB | ~280ms              |
| mxbai-rerank-large-v1    | 1.2GB | ~450ms              |
| bge-reranker-v2-m3       | 2.3GB | ~700ms              |

The right choice is the smallest model that hits your relevance
target on a labeled eval set. Larger reranker is rarely worth the
latency unless your downstream LLM cost dominates retrieval cost.
