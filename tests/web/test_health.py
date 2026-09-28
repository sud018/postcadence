"""Health checks: every way tomorrow's post could fail, found today."""
from __future__ import annotations

import dataclasses
from datetime import date, timedelta

import pytest

from agent import paths
from agent.config import load_config, save_config
from agent.state import load_state, save_state
from agent.topics import save_topics
from web import health


@pytest.fixture
def secrets(monkeypatch):
    """Pretend these secrets are stored; everything else is missing."""
    stored: set[str] = {"OPENAI_API_KEY", "LINKEDIN_ACCESS_TOKEN", "GITHUB_TOKEN"}
    monkeypatch.setattr(health, "get_secret", lambda name: "x" if name in stored else None)
    monkeypatch.setattr(health, "workflow_path", lambda: paths.DATA_DIR / "no-workflow.yml")
    return stored


def titles(found) -> list[str]:
    return [i.title for i in found]


def test_first_run_is_one_friendly_issue(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "CONFIG_FILE", tmp_path / "missing.json")
    found = health.issues()
    assert len(found) == 1
    assert found[0].href == "/setup"


def test_missing_key_is_bad(secrets):
    secrets.discard("OPENAI_API_KEY")
    found = health.issues()
    assert found[0].level == "bad"
    assert "API key" in found[0].title


def test_missing_linkedin_is_bad(secrets):
    secrets.discard("LINKEDIN_ACCESS_TOKEN")
    assert "LinkedIn is not connected" in titles(health.issues())


@pytest.mark.parametrize("days, level", [(-1, "bad"), (3, "warn"), (30, None)])
def test_token_expiry_warns_early_and_fails_late(secrets, days, level):
    cfg = load_config()
    expires = (date.today() + timedelta(days=days)).isoformat()
    save_config(dataclasses.replace(cfg, linkedin_token_expires=expires))

    found = [i for i in health.issues() if "token" in i.title.lower()]
    assert (found[0].level if found else None) == level


def test_empty_topic_list_is_bad(secrets):
    save_topics([])
    assert "No topics yet" in titles(health.issues())


def test_running_low_on_topics_is_only_info(secrets):
    state = load_state()
    state.next_topic_index = 1          # 3 topics seeded, so 2 left
    save_state(state)
    found = [i for i in health.issues() if "left" in i.title]
    assert found and found[0].level == "info"


def test_used_up_topics_warn(secrets):
    state = load_state()
    state.next_topic_index = 3
    save_state(state)
    assert "Topic list used up" in titles(health.issues())


def test_cron_drift_is_caught(secrets, monkeypatch, tmp_path):
    workflow = tmp_path / "post.yml"
    workflow.write_text('on:\n  schedule:\n    - cron: "0 3 * * *"\n', encoding="utf-8")
    monkeypatch.setattr(health, "workflow_path", lambda: workflow)
    assert "Schedule and workflow disagree" in titles(health.issues())


def test_github_missing_is_info_not_an_alarm(secrets):
    found = [i for i in health.issues() if "GitHub" in i.title]
    assert found and found[0].level == "info"


def test_worst_problems_come_first(secrets):
    secrets.discard("OPENAI_API_KEY")
    levels = [i.level for i in health.issues()]
    assert levels == sorted(levels, key=health.ORDER.get)


def test_all_clear_when_everything_is_set(secrets):
    cfg = load_config()
    save_config(dataclasses.replace(cfg, github_repo="me/agent"))
    state = load_state()
    state.next_topic_index = 0
    save_state(state)
    save_topics([f"Topic {n}" for n in range(10)])
    assert health.issues() == []
