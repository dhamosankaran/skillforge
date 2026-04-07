"""LLM provider abstraction layer."""
from typing import Protocol


class LLMProvider(Protocol):
    """Protocol for LLM providers (Gemini, Claude, etc.)."""

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The full prompt string.
            temperature: Sampling temperature (0.0 - 1.0).
            max_tokens: Maximum output tokens.
            json_mode: Whether to request JSON-formatted output.

        Returns:
            Response text string.
        """
        ...
