"""The GitHub layer: reading the remote, sealing secrets, and the device flow."""
from __future__ import annotations

import base64

import pytest
from nacl import encoding, public

from agent.github import api, device, repo_secrets
from agent.github.errors import GitHubAuthError, GitHubError

# --- finding the repo ------------------------------------------------------

HTTPS = '[remote "origin"]\n\turl = https://github.com/manikanta/linkedin-agent.git\n'
SSH = '[remote "origin"]\n\turl = git@github.com:manikanta/linkedin-agent.git\n'
GITLAB = '[remote "origin"]\n\turl = https://gitlab.com/manikanta/linkedin-agent.git\n'


@pytest.mark.parametrize("text", [HTTPS, SSH, HTTPS.replace(".git", "")])
def test_repo_is_read_from_the_git_remote(tmp_path, text):
    config = tmp_path / "config"
    config.write_text(text, encoding="utf-8")
    assert api.repo_from_remote(config) == "manikanta/linkedin-agent"


def test_missing_git_config_is_not_an_error(tmp_path):
    assert api.repo_from_remote(tmp_path / "nothing") == ""


def test_a_remote_somewhere_else_is_ignored(tmp_path):
    config = tmp_path / "config"
    config.write_text(GITLAB, encoding="utf-8")
    assert api.repo_from_remote(config) == ""


# --- sealing secrets -------------------------------------------------------

def test_sealed_value_can_only_be_opened_with_the_private_key():
    private = public.PrivateKey.generate()
    key_b64 = private.public_key.encode(encoding.Base64Encoder()).decode()

    locked = repo_secrets.seal(key_b64, "sk-super-secret")

    opened = public.SealedBox(private).decrypt(base64.b64decode(locked))
    assert opened.decode() == "sk-super-secret"


def test_sealing_the_same_value_twice_looks_different():
    """Sealed boxes are randomised, so the ciphertext leaks nothing."""
    private = public.PrivateKey.generate()
    key_b64 = private.public_key.encode(encoding.Base64Encoder()).decode()

    assert repo_secrets.seal(key_b64, "same") != repo_secrets.seal(key_b64, "same")


# --- the device flow -------------------------------------------------------

class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = str(payload)

    def json(self):
        return self._payload


def test_start_needs_a_client_id():
    with pytest.raises(GitHubAuthError):
        device.start("")


def test_start_returns_what_the_page_shows(monkeypatch):
    monkeypatch.setattr(device.requests, "post", lambda *a, **k: FakeResponse(
        {"device_code": "long", "user_code": "ABCD-1234", "interval": 5,
         "verification_uri": "https://github.com/login/device", "expires_in": 900}))

    flow = device.start("Iv1.test")
    assert flow["user_code"] == "ABCD-1234"
    assert flow["device_code"] == "long"


def test_pending_approval_is_not_an_error(monkeypatch):
    monkeypatch.setattr(device.requests, "post",
                        lambda *a, **k: FakeResponse({"error": "authorization_pending"}))
    assert device.poll_once("Iv1.test", "long") is None


def test_slow_down_also_just_means_keep_waiting(monkeypatch):
    monkeypatch.setattr(device.requests, "post",
                        lambda *a, **k: FakeResponse({"error": "slow_down"}))
    assert device.poll_once("Iv1.test", "long") is None


def test_approval_gives_back_the_token(monkeypatch):
    monkeypatch.setattr(device.requests, "post",
                        lambda *a, **k: FakeResponse({"access_token": "gho_abc"}))
    assert device.poll_once("Iv1.test", "long") == "gho_abc"


def test_a_refusal_stops_the_polling(monkeypatch):
    monkeypatch.setattr(device.requests, "post",
                        lambda *a, **k: FakeResponse({"error": "access_denied"}))
    with pytest.raises(GitHubAuthError):
        device.poll_once("Iv1.test", "long")


def test_expired_code_says_so_in_plain_words(monkeypatch):
    monkeypatch.setattr(device.requests, "post",
                        lambda *a, **k: FakeResponse({"error": "expired_token"}))
    with pytest.raises(GitHubAuthError, match="expired"):
        device.poll_once("Iv1.test", "long")


# --- the API helper --------------------------------------------------------

def test_a_rejected_token_is_an_auth_error(monkeypatch):
    monkeypatch.setattr(api.requests, "request", lambda *a, **k: FakeResponse({}, status=401))
    with pytest.raises(GitHubAuthError):
        api.call("GET", "/user", "bad")


def test_other_failures_keep_the_status_code(monkeypatch):
    monkeypatch.setattr(api.requests, "request", lambda *a, **k: FakeResponse({}, status=500))
    with pytest.raises(GitHubError, match="500"):
        api.call("GET", "/user", "token")
