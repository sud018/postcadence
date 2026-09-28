"""Anthropic provider, over plain HTTPS so no extra SDK is needed."""
from __future__ import annotations

import requests

from agent.llm.base import AuthError, LLMError, LLMProvider

API = "https://api.anthropic.com/v1"
VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    default_model = "claude-sonnet-4-5"

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key or "", "anthropic-version": VERSION,
                "content-type": "application/json"}

    def _call(self, method: str, path: str, **kwargs) -> dict:
        response = requests.request(method, f"{API}{path}", headers=self._headers(),
                                    timeout=60, **kwargs)
        if response.status_code in (401, 403):
            raise AuthError("Anthropic rejected the API key.")
        if response.status_code == 429:
            raise LLMError("Anthropic rate limit reached.")
        if response.status_code >= 300:
            raise LLMError(f"Anthropic error ({response.status_code}): {response.text[:200]}")
        return response.json()

    def generate(self, prompt: str, system: str = "", max_tokens: int = 800) -> str:
        body: dict = {"model": self.model, "max_tokens": max_tokens,
                      "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = system

        data = self._call("POST", "/messages", json=body)
        parts = [block.get("text", "") for block in data.get("content", [])]
        text = "".join(parts).strip()
        if not text:
            raise LLMError("Model returned an empty response.")
        return text

    def models(self) -> list[str]:
        data = self._call("GET", "/models?limit=100")
        ids = [item["id"] for item in data.get("data", [])]
        return sorted(ids, reverse=True) or [self.default_model]
