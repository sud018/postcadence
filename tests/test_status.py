from datetime import datetime
from zoneinfo import ZoneInfo

from agent.config import Config
from agent.state import HistoryEntry, State
from agent.status import counts, next_run, post_link, recent, streak, token_days, until

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


def entry(date_str, slot="09:00", status="posted"):
    return HistoryEntry(date=date_str, slot=slot, topic="t", status=status)


def state_with(*dates, status="posted"):
    state = State()
    for d in dates:
        state.add(entry(d, status=status))
    return state


def test_streak_is_zero_with_no_history():
    assert streak(State(), "2026-09-27") == 0


def test_streak_counts_consecutive_days():
    state = state_with("2026-09-25", "2026-09-26", "2026-09-27")
    assert streak(state, "2026-09-27") == 3


def test_streak_stops_at_a_gap():
    state = state_with("2026-09-23", "2026-09-25", "2026-09-26", "2026-09-27")
    assert streak(state, "2026-09-27") == 3


def test_streak_survives_a_day_that_has_not_posted_yet():
    state = state_with("2026-09-25", "2026-09-26")
    assert streak(state, "2026-09-27") == 2


def test_streak_breaks_after_two_missed_days():
    state = state_with("2026-09-24", "2026-09-25")
    assert streak(state, "2026-09-27") == 0


def test_streak_ignores_failed_posts():
    state = state_with("2026-09-26", "2026-09-27", status="failed")
    assert streak(state, "2026-09-27") == 0


def test_two_slots_on_one_day_count_once():
    state = State()
    state.add(entry("2026-09-27", "09:00"))
    state.add(entry("2026-09-27", "17:30"))
    assert streak(state, "2026-09-27") == 1
