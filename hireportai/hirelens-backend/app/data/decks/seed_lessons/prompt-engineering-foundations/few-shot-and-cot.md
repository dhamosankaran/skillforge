---
slug: few-shot-and-cot
title: Few-Shot and Chain-of-Thought Prompting
display_order: 0
quiz_items:
  - question: 'When does few-shot prompting outperform zero-shot, and what is the ceiling effect?'
    answer: 'Few-shot wins when the task format is unusual or when the model needs calibration on output style — labels, schema, tone, length. The ceiling: beyond ~5-10 well-chosen examples the marginal gain flattens, and on modern instruction-tuned models you often beat verbose few-shot prompts with a tighter zero-shot system message that names the format crisply.'
    question_type: free_text
    difficulty: easy
    display_order: 0
  - question: 'Which is the cleanest description of why "let''s think step by step" raises accuracy on multi-step reasoning tasks?'
    answer: 'It expands the model''s effective compute budget by letting intermediate tokens do reasoning work that single-token answers cannot.'
    question_type: mcq
    distractors:
      - 'It triggers a special chain-of-thought pathway in the model'
      - 'It reduces hallucination by limiting the answer length'
      - 'It primes the model to use external tools'
    difficulty: medium
    display_order: 1
---
## Concept

Few-shot prompting puts a small number of input/output examples in the
context window so the model imitates the format. Chain-of-thought
prompting asks the model to write its reasoning before its final answer
so the intermediate tokens act as scratch space.

Both work because of the same underlying mechanic: tokens are compute.
A single-token answer has one forward pass; a chain-of-thought answer
spreads the same problem across hundreds of tokens, so the model can
take partial steps that compose.

## Production

Two patterns that hold up:

1. **System message as the contract; few-shot as the calibration.**
   Put the role, output format, and constraints in the system message.
   Use few-shot only when the format is genuinely unusual.
2. **Hide the chain of thought when downstream consumers want clean
   output.** Ask for `<thinking>...</thinking>` or use the model's
   thinking-mode token, then strip it.

```python
SYSTEM = """You are a code reviewer.
Return JSON: {"severity": "high|medium|low", "issues": [...]}.
Think step by step inside <reasoning>...</reasoning> tags before the JSON."""

response = model.complete(SYSTEM, user_message)
json_part = response.split("</reasoning>")[-1].strip()
result = json.loads(json_part)
```

Failure modes: too many few-shot examples burn budget you'd rather
spend on retrieved context; chain-of-thought leaks into structured
outputs and breaks JSON parsing; example selection accidentally encodes
biases the test set didn't cover.

## Examples

| Task                 | Zero-shot | + CoT | + 5-shot |
|----------------------|-----------|-------|----------|
| Sentiment classify   | 0.91      | 0.91  | 0.92     |
| Math word problems   | 0.45      | 0.78  | 0.81     |
| Code bug localization | 0.62      | 0.74  | 0.77     |
| Schema-constrained extraction | 0.88 | 0.90 | 0.94 |

Pattern: classification doesn't benefit much from CoT; multi-step
reasoning benefits a lot; format-constrained tasks benefit from
few-shot mostly via output calibration.
