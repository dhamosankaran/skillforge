"""Gemini LLM provider — wraps the Google Generative AI SDK."""
from typing import Any, Dict

from app.core.config import get_settings


class GeminiProvider:
    """LLM provider backed by Google Gemini."""

    def __init__(self):
        self._client = None
        self._model_name = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            settings = get_settings()
            if not settings.gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY not configured")
            self._client = genai.Client(api_key=settings.gemini_api_key)
            self._model_name = settings.gemini_model
        return self._client, self._model_name

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
    ) -> str:
        from google.genai import types

        client, model_name = self._get_client()

        config_kwargs: Dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        return response.text or ""
