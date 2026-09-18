"""Pick the provider named in the config."""
from __future__ import annotations

from agent.config import Config
from agent.llm.base import AuthError, LLMError, LLMProvider

from agent.secrets_store import get_secret

KEY_NAMES = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "ollama": None,
}

def get_provider(cfg: Config) -> LLMProvider:
    name = cfg.llm_provider
    key_name = KEY_NAMES[name]

    api_key = get_secret(key_name) if key_name else None
    if key_name and not api_key:
        raise AuthError(
            f"No {key_name} stored. Run: python -m agent secret set {key_name}"
        )

    if name == "openai":
        from agent.llm.openai_p import OpenAIProvider
        return OpenAIProvider(api_key, cfg.llm_model)

    raise LLMError(f"Provider {name!r} is not implemented yet")