"""Multi-model LLM router — routes each AI task to the optimal model.

Fast tasks (keyword extraction, card drafts, quizzes) use a cheap/fast model.
Reasoning tasks (resume rewrites, cover letters, interviews) use a stronger model.

Provider + model are read from environment variables so they can be changed
without code changes:

    LLM_FAST_PROVIDER   / LLM_FAST_MODEL     → gemini / gemini-2.0-flash
    LLM_REASONING_PROVIDER / LLM_REASONING_MODEL → gemini / gemini-2.5-pro

Supported providers: "gemini", "anthropic", "openai".

`generate_for_task` accepts two cross-cutting kwargs added by spec #10
slice 6.10a (D-14 + D-15):

    provider_override: Optional[str] = None
        Forces dispatch to a specific provider regardless of the
        per-tier env config. Required by slice 6.10b's cross-model
        critique (Gemini gen → Anthropic critique per D-4).

    response_schema: Optional[Type[BaseModel]] = None
        Pydantic schema plumbed into Gemini's
        `types.GenerateContentConfig(response_schema=...)` for
        structured output. Closes drift D-016. Anthropic / OpenAI
        accept the kwarg but currently honor it only as a prompt
        hint — true schema enforcement is provider-side and only
        Gemini exposes it in the SDK.
"""
import logging
from typing import Optional, Type

from pydantic import BaseModel

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
    "company_name_extraction",
])

REASONING_TASKS = frozenset([
    "resume_rewrite",
    "resume_rewrite_section",
    "cover_letter",
    "interview_questions",
    "job_fit_explanation",
])


# ── Pricing table (USD per 1M tokens) ───────────────────────────────────────
#
# Consumed by `app/services/admin_analytics_service.py` for LLM spend
# estimation (spec #38 E-018b AC-3). Keep in sync with the providers' public
# pricing pages. Tier granularity matches the router's fast/reasoning split
# because `usage_logs` does not yet carry a per-row model discriminator —
# spend is estimated from summed `tokens_consumed` × the tier-blended rate.
# When per-model instrumentation lands, switch to a model-keyed lookup.
TIER_PRICE_USD_PER_1M_TOKENS: dict[str, float] = {
    # Gemini 2.5 Flash — default fast tier.
    "fast": 0.30,
    # Gemini 2.5 Pro — default reasoning tier. Blended input/output rate.
    "reasoning": 5.00,
}


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
    response_schema: Optional[Type[BaseModel]] = None,
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
    if response_schema is not None:
        # Closes drift D-016 — `response_schema` was previously dropped at
        # this layer despite spec #52 §6 calling for belt-and-suspenders
        # structured-output enforcement on the cover-letter call. Slice
        # 6.10b's lesson_gen + critique pipelines need deterministic
        # JSON-shaped output; prompt-only enforcement is too brittle for
        # 2000-token JSON payloads.
        config_kwargs["response_schema"] = response_schema
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
    response_schema: Optional[Type[BaseModel]] = None,
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
    if response_schema is not None:
        # Anthropic's Messages API does not currently expose a server-side
        # JSON-schema enforcement parameter equivalent to Gemini's
        # `response_schema`. We surface the schema as a prompt hint so
        # callers can rely on a single signature; downstream Pydantic
        # validation in the worker is the authoritative gate.
        system_msg += (
            f"\n\nThe JSON object MUST conform to this schema: "
            f"{response_schema.model_json_schema()}"
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
    response_schema: Optional[Type[BaseModel]] = None,
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
    if response_schema is not None:
        # OpenAI's structured-output mode is response_format with a JSON
        # schema; surfacing it as a prompt hint here mirrors the Anthropic
        # path. Slice 6.10b's worker validates server-side via Pydantic.
        messages.append({
            "role": "system",
            "content": (
                "The JSON object MUST conform to this schema: "
                f"{response_schema.model_json_schema()}"
            ),
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
    provider_override: Optional[str] = None,
    response_schema: Optional[Type[BaseModel]] = None,
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
        provider_override: Force dispatch to a specific provider
            (`"gemini"`, `"anthropic"`, or `"openai"`) regardless of the
            tier-resolved env config. Used by slice 6.10b's cross-model
            critique step (D-4 / D-14). Tier-resolved model name still
            applies — only the provider dispatcher is overridden, so set
            tier-appropriate `LLM_*_MODEL` env vars before flipping
            providers.
        response_schema: Optional Pydantic class plumbed into the
            provider's structured-output mechanism. Required when the
            caller depends on a deterministic JSON shape. Must be
            paired with `json_mode=True`. Closes drift D-016 (D-15).

    Returns:
        Generated text string.
    """
    if response_schema is not None and not json_mode:
        # Schema enforcement only makes sense when the provider has been
        # told to emit JSON. Failing fast here avoids silent drops in
        # provider implementations that ignore the schema without JSON.
        raise ValueError(
            "response_schema requires json_mode=True; received json_mode=False"
        )

    settings = get_settings()
    tier = _get_tier(task)

    if tier == "reasoning":
        provider = settings.llm_reasoning_provider.lower()
        model = settings.llm_reasoning_model
    else:
        provider = settings.llm_fast_provider.lower()
        model = settings.llm_fast_model

    if provider_override is not None:
        override = provider_override.lower()
        if override not in _PROVIDER_DISPATCH:
            raise ValueError(
                f"Unsupported provider_override: {provider_override!r} "
                f"(known: {sorted(_PROVIDER_DISPATCH)})"
            )
        provider = override
        # Model name stays tier-resolved — ops swap models per tier via env.

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
    if response_schema is not None:
        # Each provider dispatcher accepts response_schema; Gemini honors
        # it server-side, Anthropic / OpenAI surface it as a prompt hint.
        call_kwargs["response_schema"] = response_schema

    result = call_fn(**call_kwargs)

    logger.info("LLM call complete: task=%s, provider=%s, model=%s, response_len=%d", task, provider, model, len(result))
    return result
