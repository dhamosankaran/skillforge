---
slug: structured-output-and-tools
title: Structured Output and Tool Use
display_order: 1
quiz_items:
  - question: 'Define a Pydantic model for a function-calling tool that takes a city name and an optional unit, then show the schema you would pass to the LLM provider.'
    answer: |
      from pydantic import BaseModel, Field
      from typing import Literal

      class GetWeather(BaseModel):
          city: str = Field(..., description="Target city")
          unit: Literal["c", "f"] = Field("c", description="Temperature unit")

      schema = GetWeather.model_json_schema()
      tool = {"name": "get_weather", "description": "Fetch current weather", "parameters": schema}
    question_type: code_completion
    difficulty: medium
    display_order: 0
  - question: 'Why is forced JSON output via constrained decoding (e.g. Outlines, JSON mode, response_format) preferred over prompt-only "please return JSON" instructions in production?'
    answer: 'Prompt-only JSON is best-effort — the model occasionally returns prose, prose-wrapped JSON, or near-JSON with subtle invalidities (trailing commas, single quotes, unescaped newlines). Constrained decoding masks the next-token logits to only legal-JSON characters, so the output is parseable by definition. The cost is slightly higher latency and provider-specific syntax, both worth it for any pipeline whose downstream code calls json.loads.'
    question_type: free_text
    difficulty: hard
    display_order: 1
---
## Concept

Structured output is the bridge between an LLM and the rest of your
codebase. Three options, in order of strictness:

1. **Prompt-only "return JSON".** Easiest, least reliable.
2. **JSON mode / response_format.** Provider guarantees parseable JSON,
   but doesn't enforce your schema.
3. **Constrained decoding against a schema.** Provider guarantees the
   output matches your schema. Pydantic / function-calling APIs.

Tool use is structured output one level up: the LLM emits a function
call name plus arguments, your runtime executes the function, and the
result feeds back as a follow-up message.

## Production

The pattern:

```python
from pydantic import BaseModel
from openai import OpenAI

class ResumeFields(BaseModel):
    name: str
    years_experience: int
    skills: list[str]

client = OpenAI()
resp = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[...],
    response_format=ResumeFields,
)
fields: ResumeFields = resp.choices[0].message.parsed
```

Production pitfalls: schemas that are too permissive (Optional
everything) get garbage back; schemas that are too strict (regex
patterns, enums) cause the model to output empty arrays when it can't
satisfy the constraint; nested schemas explode token counts.

For tool-use loops, cap the number of iterations and log every tool
call — runaway tool loops are both a cost and a correctness hazard.

## Examples

| Use case                | Approach                       |
|-------------------------|--------------------------------|
| Resume field extraction | response_format=Pydantic model |
| SQL generation          | Constrained grammar (Outlines) |
| Multi-step agent        | Tool calling with cap=8 iter   |
| Fast classification     | Logit-bias on label tokens     |

The skill is matching strictness to the cost of malformed output. A
pipeline that deletes data on bad parses needs constrained decoding;
an analytics enrichment that retries can tolerate lighter constraints.
