"""The shape every LLM provider must fit"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMError(RuntimeError):
    """Something went wrong talking to the model"""

class AuthError(LLMError):
    """The APIKEY is missing, wrong or rejected"""

class LLMProvider(ABC):
    """Base class. Each provider fills in the name, default model and generate()"""

    name: str =""
    default_model: str =""

    def __init__(self, api_key: str|None, model: str="") -> None:
        self.api_key=api_key
        self.model = model or self.default_model

    @abstractmethod
    def generate(self, prompt: str, system: str="", max_tokens: int = 800) -> str:
        """Send the prompt to the model and return its text reply."""

    def check(self) -> str:
        """Prove the key works by asking for one short word."""
        reply = self.generate("Reply with the single word: ready", max_tokens=10)
        return reply.strip()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.model!r}>"
