from unittest.mock import patch

from fastapi.testclient import TestClient

from agent.config import load_config
from agent.llm.base import AuthError
from web.app import app

client = TestClient(app)


class FakeProvider:
    """Stands in for a real model so tests never call an API."""

    def __init__(self, reply="ready", models=("gpt-4o-mini", "gpt-4o")):
        self._reply, self._models = reply, list(models)

    def check(self):
        return self._reply

    def models(self):
        return self._models


def test_setup_page_lists_every_provider():
    body = client.get("/setup").text
    for name in ("OpenAI", "Anthropic", "Google", "Ollama"):
        assert name in body


def test_a_working_key_is_stored_and_offers_models():
    with patch("agent.llm.openai_p.OpenAIProvider", return_value=FakeProvider()), \
         patch("web.routers.wizard.set_secret") as stored:
        response = client.post("/setup/provider",
                               data={"provider": "openai", "api_key": "sk-test-123"})

    assert "Key works" in response.text
    assert "gpt-4o-mini" in response.text
    assert stored.called


def test_a_bad_key_is_not_stored():
    def explode(*args, **kwargs):
        raise AuthError("OpenAI rejected the api key")

    with patch("agent.llm.openai_p.OpenAIProvider", side_effect=explode), \
         patch("web.routers.wizard.set_secret") as stored:
        response = client.post("/setup/provider",
                               data={"provider": "openai", "api_key": "sk-wrong"})

    assert "rejected" in response.text
    assert not stored.called


def test_an_empty_key_asks_for_one():
    with patch("web.routers.wizard.get_secret", return_value=None):
        response = client.post("/setup/provider", data={"provider": "openai", "api_key": ""})
    assert "Paste a key" in response.text


def test_choosing_a_model_saves_it():
    response = client.post("/setup/model", data={"model": "gpt-4o"})
    assert "gpt-4o" in response.text
    assert load_config().llm_model == "gpt-4o"
