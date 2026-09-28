from __future__ import annotations

from agent.llm.base import AuthError, LLMError, LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"
    default_model = "gpt-4o-mini"

    def _client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError("OpenAI package is missing. Run: pip install openai") from exc
        return OpenAI(api_key=self.api_key)

    def generate(self, prompt: str, system: str="", max_tokens: int = 800) -> str:
        from openai import APIError, AuthenticationError, RateLimitError

        messages=[]
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._client().chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
            )
        except AuthenticationError as exc:
            raise AuthError("OpenAI rejected the api key") from exc
        except RateLimitError as exc:
            raise LLMError("OpenAI rate limit or quota exceeded.") from exc
        except APIError as exc:
            raise LLMError(f"OpenApi error {exc}") from exc

        text = (response.choices[0].message.content or "").strip()
        if not text:
            raise LLMError("Model returned an Empty response")
        return text

    def models(self) -> list[str]:
        """Chat models this key can use, newest-looking first."""
        from openai import APIError, AuthenticationError

        try:
            listed = self._client().models.list()
        except AuthenticationError as exc:
            raise AuthError("OpenAI rejected the api key") from exc
        except APIError as exc:
            raise LLMError(f"Could not list models: {exc}") from exc

        ids = [m.id for m in listed.data if m.id.startswith(("gpt-", "o1", "o3", "o4"))]
        skip = ("audio", "realtime", "transcribe", "tts", "image", "search", "instruct")
        usable = [i for i in ids if not any(word in i for word in skip)]
        return sorted(usable) or [self.default_model]
