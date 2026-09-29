"""The punctuality page: everything you paste elsewhere, computed not typed."""
from __future__ import annotations

import dataclasses

import pytest
from fastapi.testclient import TestClient

from agent.config import load_config, save_config
from web.app import app
from web.routers import trigger

client = TestClient(app)


@pytest.fixture
def connected(monkeypatch):
    save_config(dataclasses.replace(load_config(), github_repo="me/agent"))
    monkeypatch.setattr(trigger, "_token", lambda: "ghp_test")


def test_the_page_opens_without_github(monkeypatch):
    monkeypatch.setattr(trigger, "_token", lambda: "")
    assert client.get("/setup/trigger").status_code == 200


def test_it_shows_a_placeholder_until_the_repo_is_known(monkeypatch):
    monkeypatch.setattr(trigger, "_token", lambda: "")
    save_config(dataclasses.replace(load_config(), github_repo=""))
    assert "YOUR-NAME/YOUR-REPO" in client.get("/setup/trigger").text


def test_it_fills_in_the_real_repo(connected):
    body = client.get("/setup/trigger").text
    assert "/repos/me/agent/actions/workflows/post.yml/dispatches" in body


def test_it_prints_the_times_to_enter(connected):
    save_config(dataclasses.replace(load_config(), posts_per_day=1, post_times=["10:00"],
                                    mode="preview", preview_minutes=30))
    body = client.get("/setup/trigger").text
    for moment in ("09:30", "10:00", "10:30"):
        assert moment in body


def test_it_names_the_timezone_the_service_must_use(connected):
    save_config(dataclasses.replace(load_config(), timezone="Asia/Kolkata"))
    assert "Asia/Kolkata" in client.get("/setup/trigger").text


def test_it_asks_for_the_narrow_token_scope(connected):
    body = client.get("/setup/trigger").text
    assert "Actions: Read and write" in body
    assert "Only select repositories" in body


def test_the_test_button_needs_a_connection(monkeypatch):
    monkeypatch.setattr(trigger, "_token", lambda: "")
    response = client.post("/setup/trigger/test", follow_redirects=False)
    assert "error=" in response.headers["location"]


def test_the_test_button_sends_a_dry_run(connected, monkeypatch):
    """Proving the wiring must never cost a real post."""
    sent = {}
    monkeypatch.setattr(trigger.dispatch, "run_now",
                        lambda repo, token, dry_run=False: sent.update(repo=repo, dry_run=dry_run))

    response = client.post("/setup/trigger/test", follow_redirects=False)

    assert sent == {"repo": "me/agent", "dry_run": True}
    assert "done=" in response.headers["location"]


def test_a_refused_token_is_explained_not_swallowed(connected, monkeypatch):
    from agent.github.errors import GitHubAuthError

    def refuse(*args, **kwargs):
        raise GitHubAuthError("GitHub refused the token (403).")

    monkeypatch.setattr(trigger.dispatch, "run_now", refuse)
    response = client.post("/setup/trigger/test", follow_redirects=False)
    assert "error=" in response.headers["location"]
    assert "403" in response.headers["location"]


def test_the_schedule_page_points_here():
    assert "/setup/trigger" in client.get("/setup/schedule").text


def test_settings_points_here():
    assert "/setup/trigger" in client.get("/settings").text
