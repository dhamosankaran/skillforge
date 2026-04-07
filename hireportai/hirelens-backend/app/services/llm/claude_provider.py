"""Claude LLM provider — wraps the Anthropic SDK."""
from app.core.config import get_settings


class ClaudeProvider:
    """LLM provider backed by Anthropic Claude."""

    def __init__(self):
        self._client = None
        self._model = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            settings = get_settings()
            if not settings.anthropic_api_key:
                raise RuntimeError("ANTHROPIC_API_KEY not configured")
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            self._model = settings.claude_model
        return self._client, self._model

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
    ) -> str:
        client, model = self._get_client()

        # Claude doesn't have a native JSON mode — use system prompt hint
        system_msg = "You are a helpful assistant."
        if json_mode:
            system_msg = (
                "You are a helpful assistant that always responds with valid JSON. "
                "Do not include any text outside the JSON object."
            )

        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_msg,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from the response
        return message.content[0].text if message.content else ""
