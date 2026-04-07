"""LLM provider factory — returns the configured provider instance."""
from functools import lru_cache

from app.core.config import get_settings


@lru_cache()
def get_llm_provider():
    """Return the LLM provider based on the LLM_PROVIDER env var.

    Supported values: "gemini" (default), "claude".
    """
    settings = get_settings()
    provider_name = settings.llm_provider.lower()

    if provider_name == "claude":
        from app.services.llm.claude_provider import ClaudeProvider
        return ClaudeProvider()
    else:
        from app.services.llm.gemini_provider import GeminiProvider
        return GeminiProvider()
