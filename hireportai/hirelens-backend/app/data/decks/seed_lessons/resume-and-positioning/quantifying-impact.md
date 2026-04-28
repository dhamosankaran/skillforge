---
slug: quantifying-impact
title: Quantifying Impact on a Senior-Engineering Resume
display_order: 0
quiz_items:
  - question: 'A resume bullet reads "Improved API performance significantly." Rewrite it to senior-engineering quality.'
    answer: 'Cut p99 API latency from 480ms to 120ms (4x reduction) by introducing request-level coalescing and a Redis L2 cache, sustaining 40K RPS through Black Friday at 0.02% error rate.'
    question_type: free_text
    difficulty: medium
    display_order: 0
  - question: 'When you do not have access to the underlying numbers, what is the next-best move?'
    answer: 'Use proxies — relative deltas ("3x faster"), team size or scope ("partnered with 4 product squads"), or qualitative outcomes the reader can verify against the rest of your timeline ("shipped before the Q3 board review"). Made-up numbers are worse than no numbers; recruiters detect them and discount the rest of the bullet.'
    question_type: free_text
    difficulty: easy
    display_order: 1
---
## Concept

The single biggest gap between junior and senior resumes is
quantification. A senior bullet answers three questions in one
sentence: what did you do, how did you measure it, and how big was it?

Hiring managers skim. They are looking for evidence that you operate at
the level you claim. Numbers carry that evidence faster than adjectives
can. "Significantly improved" is a claim; "p99 from 480ms → 120ms" is
proof.

## Production

The XYZ frame: accomplished X, as measured by Y, by doing Z.

- **X** — the outcome. Latency cut, revenue lifted, churn reduced.
- **Y** — the unit and baseline. p99 ms, monthly recurring revenue,
  cohort retention.
- **Z** — the technical lever. The thing only you understand.

Strong bullets do all three:

- Reduced data-pipeline cost from $42K/mo to $14K/mo (-67%) by
  migrating Spark jobs to DuckDB on a single c6id.16xlarge.
- Lifted onboarding completion from 38% to 61% over 6 weeks by
  collapsing 4 setup steps into 1 and adding a contextual progress
  hint.
- Cut deploy lead time from 47min to 8min by parallelizing test
  shards and gating only on smoke-suite green.

Weak bullets miss one or two of XYZ:

- "Improved performance" — no Y, no Z.
- "Used Kubernetes for deployments" — no X, no Y.
- "Drove 40% improvement" — no Y, no Z. 40% of what?

## Examples

| Weak                                | Strong                                                                 |
|-------------------------------------|------------------------------------------------------------------------|
| Built a chat feature                | Shipped a real-time chat surface that became the #2 retention driver  |
| Improved test reliability           | Cut flaky-test rate from 8% → 0.4% via test-isolation refactor        |
| Helped scale the team               | Hired and onboarded 6 ICs in 9 months, all promoted within 18 months  |
| Worked on machine learning          | Replaced linear-regression CTR model with two-tower DNN; +12% CTR      |

The discipline is honesty about which metrics moved and which didn't.
Cherry-picking a vanity metric is a worse signal than admitting the
project taught you something but didn't ship a number worth quoting.
