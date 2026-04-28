---
slug: tech-lead-tradeoffs
title: Tech-Lead Trade-offs on AI Teams
display_order: 0
quiz_items:
  - question: 'A tech lead is choosing between building a custom RAG pipeline and adopting LangChain or LlamaIndex for a new product feature. What questions should drive the decision?'
    answer: 'Three questions: (1) How much of the framework do we actually need? Frameworks earn their keep when you use 70%+ of their abstractions; you''ll fight them if you only use 20%. (2) How stable is the framework''s API and team? LangChain has had multiple breaking re-architectures; that''s a real cost. (3) Can the team debug a failure that originates inside the framework? If the answer is "no, we''d ship a workaround", the framework will produce more incidents than it saves engineering hours. The decision is rarely binary — many teams use a framework for 30% of the surface (e.g. document loaders, splitters) and write their own retrieval / reranker / orchestration where the value lives.'
    question_type: free_text
    difficulty: medium
    display_order: 0
  - question: 'When is "build" the right answer over "buy" for an AI/ML capability?'
    answer: 'When the capability is part of the differentiated product surface (your retrieval quality, your eval methodology, your fine-tuned model), when the buy option locks you to a vendor''s roadmap that you can''t influence, or when the buy option''s data-flow requires sending sensitive customer data to a third party your security review won''t approve. Build is the right answer for capabilities that compose with your moat; buy is right for commodity infrastructure (vector DB, observability, basic LLM access) where the vendor is incentivized to be cheaper and faster than your team can be.'
    question_type: free_text
    difficulty: hard
    display_order: 1
---
## Concept

Tech-lead decisions on AI teams have a different shape than on
classical software teams. The non-determinism of LLM outputs means
many trade-offs that were "ship and measure" elsewhere become "design
the eval before shipping". The fast-moving model landscape means
infrastructure choices that look reasonable today are deprecated in
six months.

The TL's job is to anchor the team to durable choices and surface the
ones that will need to be revisited.

## Production

Three trade-offs that recur:

1. **Framework vs first-principles.** Frameworks (LangChain, LlamaIndex,
   Haystack) accelerate the first 70% of a use case and make the last
   30% harder than writing it yourself. Decision: use the framework
   only for the parts where you'd write code that looks the same
   anyway (loaders, splitters, vector store wrappers). Write the
   retrieval / orchestration / eval surface.
2. **Hosted vs self-hosted models.** Hosted (OpenAI, Anthropic, Gemini)
   gives best-in-class quality and pricing but couples you to a roadmap
   you don't control. Self-hosted (Llama, Qwen) gives control but
   demands an inference-engineering investment. Most teams should
   start hosted and pay attention to the per-feature cost — the
   crossover for justified self-hosting is usually around $50-100K/mo
   in API spend with predictable workload.
3. **Build vs buy on the eval / observability layer.** Tools like
   LangSmith, Braintrust, Helicone are improving fast. The right
   default is to start with a vendor for week-one observability and
   reserve build effort for the eval methodology where you have
   domain expertise the vendor can't.

## Examples

| Decision                 | Default                           | Revisit when                       |
|--------------------------|-----------------------------------|------------------------------------|
| Framework adoption       | First-principles for core surface | Team grows past 5 LLM engineers    |
| Hosted vs self-hosted    | Hosted                            | API spend > $50K/mo + stable workload |
| Eval tooling             | Vendor (Braintrust, LangSmith)    | Domain-specific eval needs        |
| Vector DB                | pgvector if Postgres-native       | Latency or scale forces a switch  |

The TL skill is naming the revisit triggers explicitly. "We're using
hosted Anthropic; revisit if monthly spend exceeds $40K or if a
24-hour outage costs more than $250K." That's the artifact that lets
future decisions be calibrated, not re-litigated.
