---
slug: caching-and-cost-controls
title: Caching and Cost Controls
display_order: 1
quiz_items:
  - question: 'Why is exact-match prompt caching usually insufficient for production LLM workloads, and what is the next layer up?'
    answer: 'Exact-match caching only hits when two requests are byte-identical, which is rare in real traffic — small prompt edits, timestamps, user IDs in the prompt all bust the cache. The next layer is semantic caching: hash the embedding of the user query (not the full prompt), and serve from cache when the cosine similarity to a cached query exceeds a threshold and the system prompt is identical. Semantic caching can hit 30-60% of traffic on FAQ-style workloads where exact-match hits 2-5%.'
    question_type: free_text
    difficulty: medium
    display_order: 0
  - question: 'Implement a token-bucket rate limiter for LLM cost control that limits a user to N tokens per minute, returning the wait time if denied.'
    answer: |
      import time
      from dataclasses import dataclass

      @dataclass
      class TokenBucket:
          capacity: int
          refill_rate: float  # tokens per second
          tokens: float = 0.0
          last_refill: float = 0.0

          def consume(self, n: int) -> tuple[bool, float]:
              now = time.monotonic()
              elapsed = now - self.last_refill
              self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
              self.last_refill = now
              if self.tokens >= n:
                  self.tokens -= n
                  return True, 0.0
              wait = (n - self.tokens) / self.refill_rate
              return False, wait
    question_type: code_completion
    difficulty: hard
    display_order: 1
---
## Concept

Three layers of cost control compose:

1. **Exact-match prompt cache.** Byte-identical requests serve from
   cache. 1-5% hit rate in production.
2. **Semantic prompt cache.** Hash by query embedding; serve when
   cosine to a cached entry exceeds a threshold. 30-60% hit rate on
   FAQ-shaped workloads, 5-15% on general.
3. **Per-user / per-tier rate limits.** Token-bucket on tokens/minute,
   plus daily budget caps with circuit-breaker fallback to a smaller
   model when the cap is hit.

The art is layering them so the cheapest hit comes first. A request
checks exact-match, then semantic, then rate-limit, then dispatches to
the LLM.

## Production

```python
async def serve_query(user_id: str, query: str) -> str:
    if cached := await exact_cache.get(query):
        return cached
    if cached := await semantic_cache.get(embed(query), threshold=0.95):
        return cached
    ok, wait_s = await user_bucket.consume(estimate_tokens(query))
    if not ok:
        return await fallback_smaller_model(query)
    response = await llm.complete(query)
    await exact_cache.set(query, response, ttl=3600)
    await semantic_cache.set(embed(query), response, ttl=3600)
    return response
```

Operational gotchas:

- **Cache TTLs.** Too long and stale answers leak; too short and the
  cache doesn't earn its keep. 1-24 hours is the typical band.
- **PII in cached responses.** Cache by (system_prompt, query) pair,
  never by `(user_id, query)` unless you mean to.
- **Fallback model quality.** The smaller model has to be good enough
  that fallback isn't a visible quality cliff to users.

## Examples

| Layer                 | Hit rate | Latency saved | Cost saved   |
|-----------------------|----------|---------------|--------------|
| Exact-match cache     | 2-5%     | full          | full         |
| Semantic cache (0.95) | 30-50%   | full          | full         |
| Provider prompt cache | 60-90%*  | partial       | input tokens |
| Smaller fallback      | n/a      | n/a           | 60-95%       |

\*Provider prompt caching (Anthropic, OpenAI) is the cheapest win for
system-prompt-heavy workloads — input tokens billed at 10% when cached.
Always enabled before considering anything more elaborate.
