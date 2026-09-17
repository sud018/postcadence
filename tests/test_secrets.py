import pytest

from agent import secrets_store


def test_env_var_wins(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env-123456")
    assert secrets_store.get_secret("OPENAI_API_KEY") == "sk-from-env-123456"


def test_unknown_secret_rejected():
    with pytest.raises(KeyError):
        secrets_store.get_secret("OPENAI_KEY_TYPO")


@pytest.mark.parametrize("value,expected", [
    (None, "(not set)"),
    ("short", "*****"),
    ("sk-abc123xyz789", "sk-a…z789"),
])
def test_mask(value, expected):
    assert secrets_store.mask(value) == expected
