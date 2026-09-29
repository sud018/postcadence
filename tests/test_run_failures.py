"""A failure that leaves no trace looks exactly like a quiet day. It must not."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

import pytest

from agent import run
from agent.config import Config
from agent.preview import Draft, PreviewError
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


# --- the review clock runs from the draft, not from the wall clock ---------


def draft_open_for(minutes: float, decision: str = "none") -> Draft:
    opened = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return Draft(number=7, text="the post", decision=decision,
                 created_at=opened.isoformat().replace("+00:00", "Z"))


def test_a_fresh_draft_is_not_published_immediately(monkeypatch):
    """A draft written late still gets its full review window.

    Otherwise one run would open the issue and publish it in the same breath,
    and 'let me review first' would mean nothing.
    """
    monkeypatch.setattr(run.preview, "open_draft", lambda *a, **k: draft_open_for(0))

    result = run.decide_preview(CFG, "09:00")

    assert result.status == "waiting"
    assert "min of review time left" in result.reason
    assert failures() == []                       # waiting is not failing


def test_the_draft_publishes_once_the_window_has_passed(monkeypatch):
    published = {}
    monkeypatch.setattr(run.preview, "open_draft", lambda *a, **k: draft_open_for(31))
    monkeypatch.setattr(run, "publish", lambda cfg, pick, slot, text, date: published.setdefault("text", text) or "urn:1")
    monkeypatch.setattr(run.preview, "close_draft", lambda *a, **k: None)

    result = run.decide_preview(CFG, "09:00")

    assert result.status == "posted"
    assert published["text"] == "the post"


def test_an_explicit_approval_does_not_wait(monkeypatch):
    """You already answered - there is nothing left to wait for."""
    monkeypatch.setattr(run.preview, "open_draft", lambda *a, **k: draft_open_for(2, "approve"))
    monkeypatch.setattr(run, "publish", lambda *a, **k: "urn:1")
    monkeypatch.setattr(run.preview, "close_draft", lambda *a, **k: None)

    assert run.decide_preview(CFG, "09:00").status == "posted"


def test_an_explicit_cancel_does_not_wait_either(monkeypatch):
    monkeypatch.setattr(run.preview, "open_draft", lambda *a, **k: draft_open_for(2, "cancel"))
    monkeypatch.setattr(run.preview, "close_draft", lambda *a, **k: None)

    assert run.decide_preview(CFG, "09:00").status == "skipped"


def test_waiting_leaves_the_slot_open_for_the_next_run(monkeypatch):
    monkeypatch.setattr(run.preview, "open_draft", lambda *a, **k: draft_open_for(5))
    run.decide_preview(CFG, "09:00")
    assert load_state().already_handled(TODAY, "09:00") is False


def test_a_day_of_late_runs_still_gets_the_post_out(monkeypatch):
    """Replay of 28 September 2026, when GitHub ran every tick 80-110 min late.

    Under the old rules the draft was never written and nothing was published.
    Now the first late run opens the draft, and a later run publishes it once
    the review window has actually elapsed.
    """
    issues: dict[int, Draft] = {}
    clock = {"now": datetime.now(timezone.utc)}

    def fake_open(date, slot, token="", repo=""):
        return issues.get(1)

    def fake_create(date, slot, topic, text, action, minutes, token="", repo=""):
        issues[1] = Draft(number=1, text=text, decision="none",
                          created_at=clock["now"].isoformat().replace("+00:00", "Z"))
        return 1

    monkeypatch.setattr(run.preview, "open_draft", fake_open)
    monkeypatch.setattr(run.preview, "create_draft", fake_create)
    monkeypatch.setattr(run.preview, "close_draft", lambda *a, **k: None)
    monkeypatch.setattr(run, "compose", lambda cfg, slot, state=None: (Pick("Topic", False, 0), "the post"))
    monkeypatch.setattr(run, "publish", lambda *a, **k: "urn:li:share:1")

    # tick one, 80 minutes late: the draft finally gets written
    run.prepare_preview(CFG, "09:00")
    assert 1 in issues
    assert run.decide_preview(CFG, "09:00").status == "waiting"

    # tick two, 12 minutes later: still inside the review window
    clock["now"] += timedelta(minutes=12)
    monkeypatch.setattr(run.preview, "open_draft",
                        lambda *a, **k: Draft(1, "the post", "none",
                                              (clock["now"] - timedelta(minutes=12))
                                              .isoformat().replace("+00:00", "Z")))
    assert run.decide_preview(CFG, "09:00").status == "waiting"

    # tick three: the full 30 minutes have passed, so it goes out
    monkeypatch.setattr(run.preview, "open_draft",
                        lambda *a, **k: Draft(1, "the post", "none",
                                              (clock["now"] - timedelta(minutes=45))
                                              .isoformat().replace("+00:00", "Z")))
    assert run.decide_preview(CFG, "09:00").status == "posted"


def test_a_draft_written_this_second_is_not_judged_in_the_same_run(monkeypatch):
    """28 September, run at 23:35, verbatim from the log:

        Draft 18:30: drafted - issue #4
        === 18:30 === failed
        No draft issue was found, so there was nothing to publish.

    Both lines, 0.4 seconds apart, in one run. GitHub's issue list had not
    caught up with the issue it had just created - and even if it had, a draft
    nobody has seen yet must not be judged. run-due now leaves a slot it has
    just drafted to the next run.
    """
    from agent.cli.posting import cmd_run_due

    drafted, decided = [], []
    monkeypatch.setattr("agent.cli.posting.load_config", lambda: CFG)
    monkeypatch.setattr("agent.cli.posting.prepare_slots",
                        lambda cfg, state: [(TODAY, "09:00")])
    monkeypatch.setattr("agent.cli.posting.due_slots",
                        lambda cfg, state: [(TODAY, "09:00")])
    monkeypatch.setattr("agent.cli.posting.prepare_preview",
                        lambda cfg, slot, date: drafted.append(slot)
                        or run.RunResult(status="drafted", topic="t", reason="issue #4"))
    monkeypatch.setattr("agent.cli.posting.decide_preview",
                        lambda cfg, slot, date: decided.append(slot)
                        or run.RunResult(status="posted", topic="t"))

    cmd_run_due(argparse.Namespace(dry_run=False))

    assert drafted == ["09:00"]
    assert decided == []          # left for the next run, not published blind
