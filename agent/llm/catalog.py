"""Model names to offer before a key has been verified.

Once a key is checked, the live list from the provider replaces these.
Keep the first entry of each list as the sensible default.
"""

KNOWN_MODELS = {
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "o4-mini"],
    "anthropic": ["claude-sonnet-4-5", "claude-haiku-4-5", "claude-opus-4-1"],
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
    "ollama": ["llama3.1", "qwen2.5", "mistral", "phi4"],
}


def known_models(provider: str) -> list[str]:
    return KNOWN_MODELS.get(provider, [])
