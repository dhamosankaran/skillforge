---
description: LLM task tiering, provider routing, and the generate_for_task() interface
---
# LLM Strategy Skill

## Overview
All LLM calls in the backend are routed through a single task-based
router (`app/core/llm_router.py`). Callers never pick a provider or
model directly — they pass a **task name** and the router maps it to
a tier (fast or reasoning) and dispatches to the configured provider
(Gemini, Anthropic, or OpenAI). This lets ops swap models globally
via environment variables without touching code.

## Key File
- `app/core/llm_router.py`

## Tiers

### FAST_TASKS — low-latency, cheap model
Used for high-volume, deterministic extraction / drafting:
- `ats_keyword_extraction` — parse a JD into ATS keywords
- `card_draft` — generate flashcard Q/A drafts for admin
- `quiz_generation` — create quick quiz prompts
- `gap_mapping` — map missing skills to flashcard categories
- `rewrite_bullets` — rewrite resume bullets for impact
- `experience_narrative` — 1-2 sentence "My Experience" bullet
  (moved from reasoning tier in P5-S11; output is short and the
  reasoning-tier model wasted budget on hidden thinking tokens)
- `company_name_extraction` — extract the hiring company from a JD
  (B-024 — LLM primary, regex fallback on infra failure, null on
  unclear; aggregator deny-list backstop server-side)

### REASONING_TASKS — stronger reasoning model
Used for longer, creative, or multi-step outputs:
- `resume_rewrite` — full resume rewrite against a JD
- `resume_rewrite_section` — per-section rewrite (spec #51)
- `cover_letter` — tailored cover letter
- `interview_questions` — interview prep question set
- `job_fit_explanation` — Analysis Results fit/strengths/gaps/plan
  (promoted from fast in B-022 — reasoning quality matches the rest of
  the Analysis Results surface; requires `thinking_budget` to avoid
  B-014-class empty-output failures on Gemini 2.5 Pro)

Unknown task names default to the **fast** tier.

## Public Interface

```python
from app.core.llm_router import generate_for_task

text = generate_for_task(
    task="resume_rewrite",             # tier selector
    prompt="<user prompt>",
    system_prompt="<optional system>", # optional
    json_mode=False,                   # force JSON response
    max_tokens=4096,
    temperature=0.7,
)
```

Return type is always a plain string (JSON-serialized text when
`json_mode=True`). The router handles provider-specific quirks
internally (e.g., Gemini JSON mode, Anthropic system prompts).

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `LLM_FAST_PROVIDER` | Provider for fast tier | `gemini` |
| `LLM_FAST_MODEL` | Model for fast tier | `gemini-2.0-flash` |
| `LLM_REASONING_PROVIDER` | Provider for reasoning tier | `gemini` |
| `LLM_REASONING_MODEL` | Model for reasoning tier | `gemini-2.5-pro` |
| `GEMINI_API_KEY` | Required if either tier uses Gemini | — |
| `ANTHROPIC_API_KEY` | Required only if a tier uses Anthropic | — |
| `OPENAI_API_KEY` | Required only if a tier uses OpenAI | — |

Provider dispatch is a dict of `{"gemini", "anthropic", "openai"}`
handlers; swap by setting the env var, no code change needed.

## Callers (where each task is used)

| Task | Caller (`app/services/`) |
|------|--------------------------|
| `ats_keyword_extraction` | `ai_service.py`, `gpt_service.py` |
| `resume_rewrite` | `ai_service.py`, `gpt_service.py` |
| `resume_rewrite_section` | `gpt_service.py` |
| `cover_letter` | `ai_service.py`, `gpt_service.py` |
| `interview_questions` | `ai_service.py`, `gpt_service.py` |
| `rewrite_bullets` | `ai_service.py`, `gpt_service.py` |
| `job_fit_explanation` | `gpt_service.py` (Analysis Results) |
| `card_draft` | `ai_card_service.py` |
| `gap_mapping` | `gap_mapping_service.py` |
| `experience_narrative` | `experience_service.py` |
| `quiz_generation` | `study_service.py` (quiz mode) |
| `company_name_extraction` | `nlp.py` (via `extract_job_requirements`; both cover-letter prompt and tracker autopopulate inherit) |

## Switching Providers
To move reasoning tasks from Gemini 2.5 Pro to Claude Sonnet:
```
LLM_REASONING_PROVIDER=anthropic
LLM_REASONING_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-...
```
Redeploy. Fast tier keeps running on Gemini Flash. No code touched.

## Rules
- **Never** import provider SDKs directly from service code — always
  call `generate_for_task()`.
- **Never** call `get_llm_provider()` directly; that helper exists
  only for the router itself.
- When adding a new LLM-powered feature, decide its tier **first**,
  add the task name to the relevant list in `llm_router.py`, and
  then call `generate_for_task(task="...", ...)`.
