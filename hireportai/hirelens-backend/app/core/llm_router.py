"""Multi-model LLM router — routes each AI task to the optimal model.

Fast tasks (keyword extraction, card drafts, quizzes) use a cheap/fast model.
Reasoning tasks (resume rewrites, cover letters, interviews) use a stronger model.

Provider + model are read from environment variables so they can be changed
without code changes:

    LLM_FAST_PROVIDER   / LLM_FAST_MODEL     → gemini / gemini-2.0-flash
    LLM_REASONING_PROVIDER / LLM_REASONING_MODEL → gemini / gemini-2.5-pro

Supported providers: "gemini", "anthropic", "openai".
"""
import logging
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ── Task-to-tier mapping ────────────────────────────────────────────────────

FAST_TASKS = frozenset([
    "ats_keyword_extraction",
    "card_draft",
    "quiz_generation",
    "gap_mapping",
    "rewrite_bullets",
    "experience_narrative",
])

REASONING_TASKS = frozenset([
    "resume_rewrite",
    "resume_rewrite_section",
    "cover_letter",
    "interview_questions",
])


def _get_tier(task: str) -> str:
    """Return 'fast' or 'reasoning' for the given task name."""
    if task in REASONING_TASKS:
        return "reasoning"
    # Unknown tasks default to fast (cheaper).
    return "fast"


# ── Provider dispatch ───────────────────────────────────────────────────────

def _call_gemini(
    prompt: str,
    model: str,
    system_prompt: Optional[str],
    json_mode: bool,
    max_tokens: int,
    temperature: float,
    thinking_budget: Optional[int] = None,
) -> str:
    from google import genai
    from google.genai import types

    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")

    client = genai.Client(api_key=settings.gemini_api_key)

    config_kwargs = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"
    if system_prompt:
        config_kwargs["system_instruction"] = system_prompt
    if thinking_budget is not None:
        # Cap the thinking-token pool so it cannot starve the output pool on
        # Gemini 2.5 Pro. `thinking_budget=0` disables thinking entirely.
        # See B-001 investigation §4(b) / spec #51 LD-4 Option A.
        try:
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_budget=thinking_budget,
            )
        except AttributeError:
            # Older google-genai versions without ThinkingConfig — skip.
            logger.warning(
                "google-genai lacks ThinkingConfig; thinking_budget ignored"
            )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    text = response.text or ""
    if not text:
        # Visibility for the silent-failure mode where Gemini returns no
        # text — typically a finish_reason like MAX_TOKENS (e.g. thinking
        # budget consumed the cap) or a SAFETY block. Callers still get
        # an empty string; downstream JSON parse will surface 503.
        logger.warning(
            "Gemini returned empty text (model=%s, json_mode=%s, max_tokens=%s); raw response=%r",
            model,
            json_mode,
            max_tokens,
            response,
        )
    return text


def _call_anthropic(
    prompt: str,
    model: str,
    system_prompt: Optional[str],
    json_mode: bool,
    max_tokens: int,
    temperature: float,
) -> str:
    import anthropic

    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    system_msg = system_prompt or "You are a helpful assistant."
    if json_mode:
        system_msg += (
            "\n\nIMPORTANT: Respond with valid JSON only. "
            "Do not include any text outside the JSON object."
        )

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_msg,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text if message.content else ""


def _call_openai(
    prompt: str,
    model: str,
    system_prompt: Optional[str],
    json_mode: bool,
    max_tokens: int,
    temperature: float,
) -> str:
    import openai

    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    client = openai.OpenAI(api_key=settings.openai_api_key)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    elif json_mode:
        messages.append({
            "role": "system",
            "content": "Respond with valid JSON only. Do not include any text outside the JSON object.",
        })
    messages.append({"role": "user", "content": prompt})

    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


_PROVIDER_DISPATCH = {
    "gemini": _call_gemini,
    "anthropic": _call_anthropic,
    "openai": _call_openai,
}


# ── Public API ──────────────────────────────────────────────────────────────

def generate_for_task(
    task: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    json_mode: bool = False,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    thinking_budget: Optional[int] = None,
) -> str:
    """Generate text using the optimal model for the given task.

    Args:
        task: Task name (e.g. "resume_rewrite", "card_draft").
        prompt: The user/content prompt.
        system_prompt: Optional system-level instruction.
        json_mode: Request JSON-formatted output.
        max_tokens: Maximum output tokens.
        temperature: Sampling temperature.
        thinking_budget: Gemini-only cap on thinking-token pool (tokens).
            Ignored by other providers. Set to a small positive integer
            (e.g. 512-2000) to stop thinking from starving the output pool
            on Gemini 2.5 Pro; set 0 to disable thinking entirely.

    Returns:
        Generated text string.
    """
    settings = get_settings()
    tier = _get_tier(task)

    if tier == "reasoning":
        provider = settings.llm_reasoning_provider.lower()
        model = settings.llm_reasoning_model
    else:
        provider = settings.llm_fast_provider.lower()
        model = settings.llm_fast_model

    call_fn = _PROVIDER_DISPATCH.get(provider)
    if call_fn is None:
        raise ValueError(f"Unsupported LLM provider: {provider!r}")

    logger.info("LLM call: task=%s, tier=%s, provider=%s, model=%s", task, tier, provider, model)

    call_kwargs = dict(
        prompt=prompt,
        model=model,
        system_prompt=system_prompt,
        json_mode=json_mode,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if provider == "gemini" and thinking_budget is not None:
        call_kwargs["thinking_budget"] = thinking_budget

    result = call_fn(**call_kwargs)

    logger.info("LLM call complete: task=%s, provider=%s, model=%s, response_len=%d", task, provider, model, len(result))
    return result
