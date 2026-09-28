"""A failure that leaves no trace looks exactly like a quiet day. It must not."""
from __future__ import annotations

import pytest

from agent import run
from agent.config import Config
from agent.preview import PreviewError
from agent.state import load_state
from agent.topics.loader import TopicError
from agent.topics.picker import Pick

CFG = Config(timezone="UTC", post_times=["09:00"], mode="preview")
TODAY = run.today_in(CFG)


def failures():
    return [h for h in load_state().history if h.status == "failed"]


def explode(message):
    def boom(*args, **kwargs):
        raise TopicError(message)
    return boom


def test_a_writer_that_fails_is_recorded_then_raised(monkeypatch):
    monkeypatch.setattr(run, "compose", explode("No topics configured."))

    with pytest.raises(TopicError):
        run.run_once(CFG, "09:00")

    [entry] = failures()
    assert entry.slot == "09:00"
    assert "Could not write the post" in entry.error


def test_a_draft_issue_that_cannot_be_opened_is_recorded(monkeypatch):
    monkeypatch.setattr(run, "compose", lambda cfg, slot, state=None: (Pick("Topic", False, 0), "text"))
    monkeypatch.setattr(run.preview, "open_draft", lambda *a, **k: None)
    monkeypatch.setattr(run.preview, "create_draft", explode_preview("Issues are disabled"))

    with pytest.raises(PreviewError):
        run.prepare_preview(CFG, "09:00")

    [entry] = failures()
    assert "Could not open the draft issue" in entry.error
    assert entry.topic == "Topic"


def explode_preview(message):
    def boom(*args, **kwargs):
        raise PreviewError(message)
    return boom


def test_a_missing_draft_at_posting_time_is_recorded(monkeypatch):
    """The 08:30 run failed, so 09:00 has nothing to publish. Say so."""
    monkeypatch.setattr(run.preview, "open_draft", lambda *a, **k: None)

    result = run.decide_preview(CFG, "09:00")

    assert result.status == "failed"
    assert "No draft issue was found" in failures()[0].error


def test_the_same_complaint_is_not_repeated(monkeypatch):
    """Four cron ticks a day must not mean four identical history lines."""
    monkeypatch.setattr(run.preview, "open_draft", lambda *a, **k: None)

    run.decide_preview(CFG, "09:00")
    run.decide_preview(CFG, "09:00")
    run.decide_preview(CFG, "09:00")

    assert len(failures()) == 1


def test_a_failure_does_not_close_the_slot(monkeypatch):
    """Failing is not the same as deciding not to post: it must be retried."""
    monkeypatch.setattr(run.preview, "open_draft", lambda *a, **k: None)
    run.decide_preview(CFG, "09:00")

    assert load_state().already_handled(TODAY, "09:00") is False


def test_two_different_failures_are_both_kept(monkeypatch):
    run.record_failure(CFG, "09:00", "Could not write the post: no key")
    run.record_failure(CFG, "09:00", "Could not open the draft issue: 403")
    assert len(failures()) == 2
