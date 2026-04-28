---
slug: eval-harness-design
title: Designing an LLM Eval Harness
display_order: 0
quiz_items:
  - question: 'What three properties should every LLM eval test case have to be useful in CI?'
    answer: 'Deterministic ground truth (the right answer must be checkable without another LLM call where possible), runtime under a reasonable budget (a 60-min eval suite is workable; an 8-hour suite gets skipped), and signal locality — when the test fails, you should know which prompt or component change caused it. Tests that fail with no clear cause get suppressed within two iterations.'
    question_type: free_text
    difficulty: medium
    display_order: 0
  - question: 'A team is choosing between LLM-as-judge and rule-based evaluation for a summarization task. Which describes the right way to combine them?'
    answer: 'Use rule-based checks for invariants the model must always satisfy (length bounds, no profanity, factual coverage of named entities) and reserve LLM-as-judge for the qualitative dimension (faithfulness, fluency) on a held-out subset. Calibrate the judge against a small human-labeled set quarterly. Pure LLM-as-judge is non-deterministic and expensive; pure rules can''t catch the failure modes that matter.'
    question_type: free_text
    difficulty: hard
    display_order: 1
---
## Concept

An eval harness is the layer that lets you change a prompt, a model,
or a chain and answer "did anything regress?" in minutes. Without one,
every change is a roll of the dice and the team's confidence in
shipping decays.

Three eval families to combine:

1. **Unit-style invariant checks.** Did the output match the schema?
   Did it stay under the length cap? Did it include the required
   named entities?
2. **Reference-comparison checks.** Distance to a gold answer (BLEU,
   ROUGE, embedding cosine, task-specific metrics like
   exact-match for QA).
3. **LLM-as-judge.** Score outputs on dimensions that resist
   programmatic evaluation — faithfulness, helpfulness, tone.

## Production

The harness pattern:

```python
@dataclass
class EvalCase:
    name: str
    prompt: str
    invariants: list[Callable[[str], bool]]
    reference: str | None = None
    judge_dimensions: list[str] | None = None

async def run_eval(case: EvalCase, model_call) -> EvalResult:
    output = await model_call(case.prompt)
    invariants_passed = all(f(output) for f in case.invariants)
    ref_score = embedding_similarity(case.reference, output) if case.reference else None
    judge_scores = await llm_judge(output, dims=case.judge_dimensions)
    return EvalResult(...)
```

Operational rules:

- **Pin the model and seed.** Eval drift caused by silent provider
  upgrades is real; either pin to a versioned model name or run twice
  and require both runs to pass.
- **Track results over time.** Per-suite pass-rate plotted over commits
  surfaces slow regressions that a green/red gate misses.
- **Sample production inputs into the suite.** A static eval set
  drifts away from real traffic; refresh quarterly.

## Examples

| Eval type             | Cost / case   | When to use                       |
|-----------------------|---------------|-----------------------------------|
| Schema invariant      | <1ms          | Always; cheapest catch            |
| Embedding similarity  | ~50ms + embed | Reference-comparison tasks        |
| Exact match / regex   | <1ms          | Classification, ID extraction     |
| LLM-as-judge          | $0.001-$0.01  | Subjective dimensions; sample     |
| Human review          | $0.5-$5       | Quarterly calibration only        |

The pattern: cheap evals at every commit, expensive evals at every
release, human evals at every quarter.
