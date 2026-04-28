---
slug: drift-and-regression-detection
title: Drift and Regression Detection in Production LLM Systems
display_order: 1
quiz_items:
  - question: 'Distinguish prompt drift, data drift, and silent model upgrades — and explain which signal in production catches each one first.'
    answer: 'Prompt drift is when downstream prompt edits inadvertently change distributions of upstream features; caught by the eval suite running on every PR. Data drift is when production input distributions shift (new user segments, new languages, longer queries); caught by feature-distribution monitors on input length, language, and embedding-cluster membership. Silent model upgrades happen when the provider rolls a model version without changing the API name; caught by canary prompts (a fixed set of 50-200 queries with stable expected outputs) that run hourly and alert on output distribution shifts.'
    question_type: free_text
    difficulty: medium
    display_order: 0
  - question: 'Implement a simple drift detector that compares the embedding centroid of the last 1000 production queries against a 7-day rolling baseline, alerting if cosine distance exceeds a threshold.'
    answer: |
      def check_drift(
          recent_embeddings: list[np.ndarray],
          baseline_centroid: np.ndarray,
          threshold: float = 0.15,
      ) -> tuple[bool, float]:
          recent_centroid = np.mean(recent_embeddings, axis=0)
          recent_centroid /= np.linalg.norm(recent_centroid) + 1e-9
          baseline = baseline_centroid / (np.linalg.norm(baseline_centroid) + 1e-9)
          distance = 1.0 - float(np.dot(recent_centroid, baseline))
          return distance > threshold, distance
    question_type: code_completion
    difficulty: medium
    display_order: 1
---
## Concept

In production, three distinct things go wrong: the prompt changed (you
know about it), the inputs changed (you might not), or the model
silently changed underneath you (you definitely don't). Each requires
its own detector.

Eval suites catch prompt regressions on PR. Feature-distribution
monitors catch input drift. Canary prompts — a fixed set of queries
with stable expected outputs run on a cadence — catch silent model
upgrades.

## Production

The three-tier monitoring stack:

1. **Per-PR eval gate.** Block merge if eval pass-rate drops more than
   1.5% from the parent commit baseline.
2. **Hourly canary.** 50-200 queries with stable outputs. Alert on:
   embedding-similarity drop vs last-known-good output, schema-
   invariant violations, or token-count distribution shift.
3. **Continuous feature-distribution monitor.** Track input length,
   language, embedding-cluster membership over a rolling window.
   Alert on KS-test p-value or cluster-membership change.

```python
import numpy as np

def check_drift(recent, baseline_centroid, threshold=0.15):
    recent_centroid = np.mean(recent, axis=0)
    recent_centroid /= np.linalg.norm(recent_centroid) + 1e-9
    baseline = baseline_centroid / (np.linalg.norm(baseline_centroid) + 1e-9)
    distance = 1.0 - float(np.dot(recent_centroid, baseline))
    return distance > threshold, distance
```

The discipline: log every (prompt, input, output, model_version,
latency, cost) tuple. Without that log, you can't reconstruct what the
system was doing the day before yesterday.

## Examples

| Signal                       | Catches                  | False-positive rate |
|------------------------------|--------------------------|---------------------|
| Eval pass-rate drop          | Prompt regressions       | Low                 |
| Canary cosine drop           | Silent model upgrade     | Medium              |
| Input-length p95 shift       | Data drift               | Medium-high         |
| Cost per query spike         | Prompt-length blow-up    | Low                 |
| Refusal-rate spike           | Safety-tuning shift      | Medium              |

The teams that ship LLM features weekly are the ones whose monitors
catch a problem before the on-call engineer's phone rings. The teams
that don't, ship monthly because every change ships a new round of
unknown unknowns.
