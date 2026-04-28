---
slug: dpo-vs-rlhf
title: DPO vs RLHF
display_order: 1
quiz_items:
  - question: 'Why has Direct Preference Optimization (DPO) largely displaced classical RLHF (PPO over a reward model) in production preference-tuning workflows?'
    answer: 'DPO collapses the two-stage RLHF pipeline (train a reward model, then PPO-fine-tune the policy against it) into a single supervised loss derived directly from preference pairs. This eliminates the reward-model artifact, removes the PPO instability that plagued classical RLHF, and brings preference tuning into the same training infrastructure as supervised fine-tuning. The cost is some loss of expressiveness — RLHF can in principle learn from a richer reward signal — but in practice DPO matches or beats PPO-RLHF on instruction-following benchmarks at a fraction of the operational complexity.'
    question_type: free_text
    difficulty: hard
    display_order: 0
  - question: 'A team has 20K human preference pairs and needs to align a fine-tuned 7B model. Which is the most defensible default?'
    answer: 'DPO with the supervised-fine-tuned model as both reference and starting policy'
    question_type: mcq
    distractors:
      - 'PPO-based RLHF with a separately trained 7B reward model'
      - 'Constitutional AI with self-critique only, no preference pairs'
      - 'Hand-tuned prompts with no preference learning at all'
    difficulty: medium
    display_order: 1
---
## Concept

Preference tuning aligns a model to human preferences by training on
pairs of (chosen, rejected) responses. Two approaches dominate:

- **RLHF (PPO over a reward model).** The classical OpenAI-paper
  pipeline: train a reward model on preferences, then run PPO
  fine-tuning of the policy against the reward model with a KL
  penalty against the original policy.
- **DPO (Direct Preference Optimization).** A single supervised loss
  derived analytically from the same RLHF objective, treating the
  policy itself as an implicit reward model. No PPO, no separate
  reward model artifact.

DPO has won on operational simplicity. RLHF still has a place for
research at frontier labs but most teams shipping aligned models
should default to DPO.

## Production

The DPO loss in pseudocode:

```python
def dpo_loss(policy_logp_chosen, policy_logp_rejected,
             ref_logp_chosen, ref_logp_rejected, beta=0.1):
    chosen_ratio   = policy_logp_chosen   - ref_logp_chosen
    rejected_ratio = policy_logp_rejected - ref_logp_rejected
    return -F.logsigmoid(beta * (chosen_ratio - rejected_ratio)).mean()
```

The reference model is the supervised-fine-tuned model you started
from; it stays frozen. `beta` controls how aggressively the model
diverges from the reference — too high collapses to the reference,
too low risks reward hacking. 0.1 is a strong default.

Operational rules:

- **Quality of preference pairs is dominant.** 20K well-curated pairs
  beat 200K noisy ones. Spend on annotation guidance, not volume.
- **Run preference tuning AFTER supervised fine-tuning.** SFT on
  high-quality demonstrations, then DPO on preferences over SFT
  outputs. Going straight to DPO from a base model under-performs.
- **Track reward delta.** During DPO, the (chosen - rejected) margin
  on a held-out set should rise; if it plateaus early, lower beta or
  add more diverse preferences.

## Examples

| Method  | Training cost | Engineering complexity | Quality (vs SFT) |
|---------|---------------|------------------------|------------------|
| SFT     | 1×            | Low                    | Baseline         |
| DPO     | 1.2×          | Low                    | +5-15% on benchmarks |
| RLHF    | 3-5×          | High (reward model + PPO) | +5-20% on benchmarks |
| RLAIF   | 2-3×          | Medium (LLM judges)    | Within range of DPO   |

The pattern: ship SFT first, layer DPO on the highest-value preference
data, reach for RLHF only when DPO has been thoroughly explored and
the residual quality gap matters more than the operational cost.
