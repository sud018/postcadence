"""Ollama provider - a model running on this machine, no key, no cost."""
from __future__ import annotations

import requests

from agent.llm.base import LLMError, LLMProvider

API = "http://localhost:11434"


class OllamaProvider(LLMProvider):
    name = "ollama"
    default_model = "llama3.1"

    def _call(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = requests.request(method, f"{API}{path}", timeout=120, **kwargs)
        except requests.RequestException as exc:
            raise LLMError("Ollama is not running. Start it with: ollama serve") from exc

        if response.status_code >= 300:
            raise LLMError(f"Ollama error ({response.status_code}): {response.text[:200]}")
        return response.json()

    def generate(self, prompt: str, system: str = "", max_tokens: int = 800) -> str:
        body = {"model": self.model, "prompt": prompt, "stream": False,
                "options": {"num_predict": max_tokens}}
        if system:
            body["system"] = system

        text = (self._call("POST", "/api/generate", json=body).get("response") or "").strip()
        if not text:
            raise LLMError("Model returned an empty response.")
        return text

    def models(self) -> list[str]:
        installed = [m["name"] for m in self._call("GET", "/api/tags").get("models", [])]
        return sorted(installed) or [self.default_model]
