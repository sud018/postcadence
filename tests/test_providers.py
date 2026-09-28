"""Every provider must fit the same shape, without any network calls."""
import pytest

from agent.llm import build
from agent.llm.base import LLMProvider
from agent.llm.catalog import known_models

NAMES = ["openai", "anthropic", "gemini", "ollama"]


@pytest.mark.parametrize("name", NAMES)
def test_every_provider_can_be_built(name):
    provider = build(name, "test-key")
    assert isinstance(provider, LLMProvider)
    assert provider.name == name


@pytest.mark.parametrize("name", NAMES)
def test_the_default_model_is_the_first_known_one(name):
    assert build(name, "k").default_model == known_models(name)[0]


@pytest.mark.parametrize("name", NAMES)
def test_an_explicit_model_wins_over_the_default(name):
    assert build(name, "k", "my-model").model == "my-model"


def test_an_unknown_provider_is_rejected():
    from agent.llm.base import LLMError
    with pytest.raises(LLMError, match="not implemented"):
        build("mystery", "k")
