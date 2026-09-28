from unittest.mock import patch

from fastapi.testclient import TestClient

from agent.config import load_config
from web.app import app
from web.routers import linkedin

client = TestClient(app, follow_redirects=False)


def test_page_shows_the_redirect_url_to_register():
    body = client.get("/setup/linkedin").text
    assert "/setup/linkedin/callback" in body
    assert "Coming soon" in body              # X, Instagram, Reddit are greyed out


def test_start_without_credentials_explains_why():
    with patch("web.routers.linkedin.get_secret", return_value=None):
        response = client.get("/setup/linkedin/start")
    assert response.status_code == 303
    assert "Client%20ID" in response.headers["location"]


def test_start_redirects_to_linkedin_with_a_state():
    with patch("web.routers.linkedin.get_secret", return_value="abc"):
        response = client.get("/setup/linkedin/start")
    location = response.headers["location"]
    assert location.startswith("https://www.linkedin.com/oauth/v2/authorization")
    assert "state=" in location and "redirect_uri=" in location


def test_callback_rejects_an_unknown_state():
    response = client.get("/setup/linkedin/callback?code=x&state=forged")
    assert "stale" in response.headers["location"]


def test_callback_passes_linkedins_own_error_through():
    response = client.get("/setup/linkedin/callback?error=user_cancelled_login"
                          "&error_description=The+user+cancelled")
    assert "cancelled" in response.headers["location"]


def test_a_good_callback_stores_the_token_and_member_id():
    linkedin._pending_states.add("good-state")
    fake = {"access_token": "tok", "member_id": "M123", "expires_on": "2027-01-01"}

    with patch("web.routers.linkedin.finish", return_value=fake), \
         patch("web.routers.linkedin.get_secret", return_value="abc"), \
         patch("web.routers.linkedin.set_secret") as stored:
        response = client.get("/setup/linkedin/callback?code=c&state=good-state")

    assert response.headers["location"] == "/setup/linkedin?connected=1"
    stored.assert_called_once_with("LINKEDIN_ACCESS_TOKEN", "tok")
    assert load_config().linkedin_member_id == "M123"
    assert "good-state" not in linkedin._pending_states    # a state is single-use


# --- the guided setup, added after the "make ten minutes feel like three" pass ---

def test_page_offers_the_details_to_paste():
    body = client.get("/setup/linkedin").text
    assert "PostCadence" in body                 # app name
    assert "postcadence-logo.png" in body        # the logo download
    assert "/setup/linkedin/callback" in body    # the redirect URL


def test_page_lists_the_four_manual_steps():
    body = client.get("/setup/linkedin").text
    for title in ("Have a LinkedIn Page", "Create the app",
                  "Request two products", "Add the redirect URL"):
        assert title in body


def test_checks_say_what_is_missing_before_anything_is_saved(monkeypatch):
    monkeypatch.setattr(linkedin, "get_secret", lambda name: "")
    body = client.post("/setup/linkedin/check").text
    assert "Not saved yet." in body
    assert "Save credentials" in body


def test_checks_ask_linkedin_once_credentials_exist(monkeypatch):
    monkeypatch.setattr(linkedin, "get_secret", lambda name: "value")
    monkeypatch.setattr(linkedin.diagnose, "probe_authorize",
                        lambda client_id, redirect: linkedin.diagnose.Result(
                            "bad", "Your app is not allowed to post yet.",
                            "Products tab - request access to 'Share on LinkedIn'."))
    monkeypatch.setattr(linkedin.diagnose, "check_token",
                        lambda *a: linkedin.diagnose.Result("ok", "Active, and allowed to post.", ""))

    body = client.post("/setup/linkedin/check").text
    assert "not allowed to post yet" in body
    assert "Share on LinkedIn" in body


def test_checks_do_not_call_linkedin_without_credentials(monkeypatch):
    called = []
    monkeypatch.setattr(linkedin, "get_secret", lambda name: "")
    monkeypatch.setattr(linkedin.diagnose, "probe_authorize", lambda *a: called.append(1))
    client.post("/setup/linkedin/check")
    assert called == []
