from datetime import datetime
from zoneinfo import ZoneInfo

from agent.config import Config
from agent.state import HistoryEntry, State
from agent.status import counts, next_run, post_link, recent, token_days, until

TZ = ZoneInfo("America/Los_Angeles")


def cfg(**kwargs) -> Config:
    base = dict(posts_per_day=2, post_times=["09:00", "17:30"], timezone="America/Los_Angeles")
    base.update(kwargs)
    return Config(**base)


def at(hour, minute=0):
    return datetime(2026, 9, 21, hour, minute, tzinfo=TZ)


def test_next_run_picks_the_next_slot_today():
    slot, when = next_run(cfg(), at(7))
    assert slot == "09:00" and when.date() == at(7).date()


def test_next_run_rolls_over_to_tomorrow_after_the_last_slot():
    slot, when = next_run(cfg(), at(20))
    assert slot == "09:00" and when.date() == at(7).date().replace(day=22)


def test_until_formats_hours_and_minutes():
    assert until(at(12, 30), at(9, 0)) == "in 3h 30m"
    assert until(at(9, 20), at(9, 0)) == "in 20m"
    assert until(at(9, 0), at(9, 30)) == "now"


def test_counts_group_by_status():
    state = State()
    state.add(HistoryEntry(date="d", slot="s", topic="t", status="posted"))
    state.add(HistoryEntry(date="d", slot="s", topic="t", status="posted"))
    state.add(HistoryEntry(date="d", slot="s", topic="t", status="failed"))
    assert counts(state) == {"posted": 2, "failed": 1}


def test_recent_is_newest_first_and_capped():
    state = State()
    for i in range(8):
        state.add(HistoryEntry(date=f"2026-09-{i + 1:02}", slot="09:00", topic=str(i), status="posted"))
    got = recent(state, limit=3)
    assert [e.topic for e in got] == ["7", "6", "5"]


def test_token_days_handles_a_missing_expiry():
    assert token_days(cfg()) is None


def test_post_link_only_when_there_is_an_id():
    posted = HistoryEntry(date="d", slot="s", topic="t", status="posted", post_id="urn:li:share:9")
    assert post_link(posted).endswith("urn:li:share:9/")
    assert post_link(HistoryEntry(date="d", slot="s", topic="t", status="failed")) == ""
