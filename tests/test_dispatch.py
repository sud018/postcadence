"""Starting the workflow from outside, because GitHub's own clock is unreliable."""
from __future__ import annotations

import dataclasses

import pytest
import yaml

from agent.config import Config
from agent.github import dispatch
from agent.schedule import trigger_times

WORKFLOW = "post.yml"


def test_the_url_points_at_the_posting_workflow():
    assert dispatch.url("me/agent") == (
        "https://api.github.com/repos/me/agent/actions/workflows/post.yml/dispatches")


def test_the_body_asks_for_whatever_is_due():
    """Not one named slot: a trigger that fires late must still do the right thing."""
    assert dispatch.body() == {"ref": "main", "inputs": {"mode": "due", "dry_run": False}}


def test_a_test_run_publishes_nothing():
    assert dispatch.body(dry_run=True)["inputs"]["dry_run"] is True


def test_a_different_default_branch_is_honoured():
    assert dispatch.body(branch="trunk")["ref"] == "trunk"


def test_run_now_posts_the_body(monkeypatch):
    sent = {}
    monkeypatch.setattr(dispatch.api, "call",
                        lambda method, path, token, **kw: sent.update(
                            method=method, path=path, token=token, **kw))

    dispatch.run_now("me/agent", "ghp_x")

    assert sent["method"] == "POST"
    assert sent["path"].endswith("/actions/workflows/post.yml/dispatches")
    assert sent["json"]["inputs"]["mode"] == "due"


def test_the_documented_headers_carry_the_token():
    assert dispatch.HEADERS["Authorization"].startswith("Bearer ")
    assert dispatch.HEADERS["Accept"] == "application/vnd.github+json"


# --- the workflow has to accept what we tell people to send -----------------

def workflow() -> dict:
    from agent import paths
    text = (paths.ROOT / ".github" / "workflows" / WORKFLOW).read_text(encoding="utf-8")
    return yaml.safe_load(text)


def test_the_workflow_accepts_the_mode_we_send():
    """If this fails, every setup guide out there is now wrong."""
    inputs = workflow()[True]["workflow_dispatch"]["inputs"]      # PyYAML reads `on:` as True
    assert dispatch.body()["inputs"]["mode"] in inputs["mode"]["options"]


def test_an_outside_trigger_runs_the_same_step_as_cron():
    """The whole point is that a punctual run and a late one behave identically."""
    steps = workflow()["jobs"]["post"]["steps"]
    [due] = [s for s in steps if s.get("name") == "Run due slots"]

    assert "schedule" in due["if"] and "due" in due["if"]
    assert due["run"].startswith("python -m agent run-due")
    # preview mode needs these to open the draft issue; the old manual path had neither
    assert "GITHUB_TOKEN" in due["env"] and "GITHUB_REPOSITORY" in due["env"]


def test_dry_run_no_longer_defaults_to_true():
    """An outside caller that omits it must post for real, not silently do nothing."""
    inputs = workflow()[True]["workflow_dispatch"]["inputs"]
    assert inputs["dry_run"]["default"] is False


# --- the times the setup page prints ----------------------------------------

def preview(times: list[str], minutes: int = 30) -> Config:
    return Config(timezone="UTC", posts_per_day=len(times), post_times=times,
                  mode="preview", preview_minutes=minutes)


def test_preview_gets_a_draft_tick_a_post_tick_and_a_spare():
    assert trigger_times(preview(["10:00"])) == ["09:30", "10:00", "10:30"]


def test_auto_mode_needs_no_draft_tick():
    cfg = Config(timezone="UTC", posts_per_day=1, post_times=["10:00"], mode="auto")
    assert trigger_times(cfg) == ["10:00", "10:30"]


def test_two_slots_are_both_covered():
    assert trigger_times(preview(["09:00", "18:30"])) == [
        "08:30", "09:00", "09:30", "18:00", "18:30", "19:00"]


def test_overlapping_slots_are_not_listed_twice():
    """Half an hour apart, so the post tick of one is the draft tick of the next."""
    assert trigger_times(preview(["09:00", "09:30"])) == ["08:30", "09:00", "09:30", "10:00"]


def test_these_are_local_times_not_utc():
    """Unlike cron_lines(), which has to emit both daylight-saving offsets.

    Los Angeles is UTC-7 in summer, so a UTC answer would say 17:00. The
    scheduling service is told the timezone and follows DST itself.
    """
    cfg = dataclasses.replace(preview(["10:00"]), timezone="America/Los_Angeles")
    assert trigger_times(cfg) == ["09:30", "10:00", "10:30"]


@pytest.mark.parametrize("minutes, expected", [
    (15, ["11:45", "12:00", "12:15"]),
    (45, ["11:15", "12:00", "12:45"]),
    (60, ["11:00", "12:00", "13:00"]),
])
def test_the_gap_follows_the_review_window(minutes, expected):
    assert trigger_times(preview(["12:00"], minutes)) == expected
