"""The GitHub page: saving the app details, signing in, pushing, sending keys."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agent.config import load_config
from agent.github.errors import GitHubAuthError
from web.app import app
from web.routers import github as page

client = TestClient(app)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No token and no network unless a test asks for them."""
    page._pending.clear()
    monkeypatch.setattr(page, "get_secret", lambda name: "")
    monkeypatch.setattr(page.api, "repo_from_remote", lambda *a, **k: "")


def connected(monkeypatch, secrets=("OPENAI_API_KEY",)):
    monkeypatch.setattr(page, "get_secret",
                        lambda name: "gho_test" if name == "GITHUB_TOKEN"
                        else ("value" if name in secrets else ""))
    monkeypatch.setattr(page.api, "current_user", lambda token: "manikanta")
    monkeypatch.setattr(page.api, "recent_runs", lambda *a, **k: [])
    monkeypatch.setattr(page.repo_secrets, "existing_secrets", lambda *a, **k: [])


def test_page_asks_for_the_client_id_first():
    body = client.get("/setup/github").text
    assert "Enable Device Flow" in body
    assert "Connect GitHub" in body


def test_saving_the_client_id_and_repo_persists_them():
    client.post("/setup/github/client",
                data={"client_id": "Iv1.abc", "repo": "me/agent"}, follow_redirects=False)
    cfg = load_config()
    assert cfg.github_client_id == "Iv1.abc"
    assert cfg.github_repo == "me/agent"


def test_the_detected_remote_is_offered(monkeypatch):
    monkeypatch.setattr(page.api, "repo_from_remote", lambda *a, **k: "me/from-remote")
    assert "me/from-remote" in client.get("/setup/github").text


def test_connect_without_a_client_id_is_refused():
    response = client.post("/setup/github/start")
    assert response.status_code == 400
    assert "error" in response.json()


def test_start_hands_the_page_the_short_code(monkeypatch):
    client.post("/setup/github/client", data={"client_id": "Iv1.abc", "repo": "me/agent"},
                follow_redirects=False)
    monkeypatch.setattr(page.device, "start", lambda client_id: {
        "device_code": "long", "user_code": "ABCD-1234",
        "verification_uri": "https://github.com/login/device", "interval": 5, "expires_in": 900})

    body = client.post("/setup/github/start").json()
    assert body["user_code"] == "ABCD-1234"
    assert page._pending["device_code"] == "long"        # the long one never reaches the page


def test_polling_reports_waiting_until_you_approve(monkeypatch):
    page._pending["device_code"] = "long"
    monkeypatch.setattr(page.device, "poll_once", lambda *a: None)
    assert client.post("/setup/github/poll").json() == {"status": "waiting"}


def test_approval_stores_the_token(monkeypatch):
    page._pending["device_code"] = "long"
    saved = {}
    monkeypatch.setattr(page.device, "poll_once", lambda *a: "gho_new")
    monkeypatch.setattr(page, "set_secret", lambda name, value: saved.update({name: value}))
    monkeypatch.setattr(page.api, "current_user", lambda token: "manikanta")

    body = client.post("/setup/github/poll").json()
    assert body == {"status": "connected", "login": "manikanta"}
    assert saved == {"GITHUB_TOKEN": "gho_new"}
    assert page._pending == {}


def test_a_refusal_clears_the_pending_sign_in(monkeypatch):
    page._pending["device_code"] = "long"

    def denied(*args):
        raise GitHubAuthError("You cancelled the approval on GitHub.")

    monkeypatch.setattr(page.device, "poll_once", denied)
    assert client.post("/setup/github/poll").status_code == 400
    assert page._pending == {}


def test_pushing_without_a_connection_is_refused():
    response = client.post("/setup/github/push", follow_redirects=False)
    assert "error=" in response.headers["location"]


def test_push_only_sends_files_that_differ(monkeypatch):
    connected(monkeypatch)
    client.post("/setup/github/client", data={"client_id": "Iv1.abc", "repo": "me/agent"},
                follow_redirects=False)

    sent = []
    monkeypatch.setattr(page, "_repo_file", lambda path: "same" if path.endswith("topics.json") else "new")
    monkeypatch.setattr(page.api, "get_file", lambda repo, path, token: ("same", "sha"))
    monkeypatch.setattr(page.api, "put_file",
                        lambda repo, path, text, message, token: sent.append(path) or "sha")

    client.post("/setup/github/push", follow_redirects=False)
    assert "data/topics.json" not in sent
    assert "data/config.json" in sent


def test_secrets_are_sealed_once_per_push(monkeypatch):
    connected(monkeypatch, secrets=("OPENAI_API_KEY", "LINKEDIN_ACCESS_TOKEN"))
    client.post("/setup/github/client", data={"client_id": "Iv1.abc", "repo": "me/agent"},
                follow_redirects=False)

    keys_fetched, pushed = [], []
    monkeypatch.setattr(page.repo_secrets, "public_key",
                        lambda repo, token: keys_fetched.append(repo) or ("key", "id"))
    monkeypatch.setattr(page.repo_secrets, "put_secret",
                        lambda repo, name, value, token, key, key_id: pushed.append(name))

    response = client.post("/setup/github/secrets", follow_redirects=False)
    assert sorted(pushed) == ["LINKEDIN_ACCESS_TOKEN", "OPENAI_API_KEY"]
    assert len(keys_fetched) == 1          # one key fetch, not one per secret
    assert "done=" in response.headers["location"]


def test_nothing_to_send_says_so(monkeypatch):
    connected(monkeypatch, secrets=())
    client.post("/setup/github/client", data={"client_id": "Iv1.abc", "repo": "me/agent"},
                follow_redirects=False)
    response = client.post("/setup/github/secrets", follow_redirects=False)
    assert "error=" in response.headers["location"]


def test_state_json_is_never_pushed():
    assert all(path != "data/state.json" for path, _ in page.SYNCED)
