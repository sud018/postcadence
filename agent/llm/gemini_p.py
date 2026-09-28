"""Google Gemini provider, over plain HTTPS."""
from __future__ import annotations

import requests

from agent.llm.base import AuthError, LLMError, LLMProvider

API = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(LLMProvider):
    name = "gemini"
    default_model = "gemini-2.5-flash"

    def _call(self, method: str, path: str, **kwargs) -> dict:
        joiner = "&" if "?" in path else "?"
        url = f"{API}{path}{joiner}key={self.api_key or ''}"
        response = requests.request(method, url, timeout=60, **kwargs)

        if response.status_code in (401, 403):
            raise AuthError("Google rejected the API key.")
        if response.status_code == 429:
            raise LLMError("Gemini rate limit reached.")
        if response.status_code >= 300:
            raise LLMError(f"Gemini error ({response.status_code}): {response.text[:200]}")
        return response.json()

    def generate(self, prompt: str, system: str = "", max_tokens: int = 800) -> str:
        body: dict = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        data = self._call("POST", f"/models/{self.model}:generateContent", json=body)
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError) as exc:
            raise LLMError("Gemini returned no usable content.") from exc

        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise LLMError("Model returned an empty response.")
        return text

    def models(self) -> list[str]:
        data = self._call("GET", "/models?pageSize=200")
        usable = [
            item["name"].removeprefix("models/")
            for item in data.get("models", [])
            if "generateContent" in item.get("supportedGenerationMethods", [])
        ]
        return sorted(usable, reverse=True) or [self.default_model]
