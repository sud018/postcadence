from datetime import datetime
from zoneinfo import ZoneInfo

from agent.config import Config
from agent.schedule import cron_lines, due_slots, slot_time
from agent.state import HistoryEntry, State

TZ = ZoneInfo("America/Los_Angeles")


def cfg(**kwargs) -> Config:
    base = dict(posts_per_day=2, post_times=["09:00", "17:30"],
                timezone="America/Los_Angeles", catch_up_hours=6)
    base.update(kwargs)
    return Config(**base)


def at(hour, minute=0, day=21):
    return datetime(2026, 9, day, hour, minute, tzinfo=TZ)


def posted(slot, date="2026-09-21"):
    return HistoryEntry(date=date, slot=slot, topic="t", status="posted")


def test_nothing_due_before_the_first_slot():
    assert due_slots(cfg(), State(), at(8, 59)) == []


def test_slot_is_due_right_after_its_time():
    assert due_slots(cfg(), State(), at(9, 1)) == ["09:00"]


def test_late_run_still_catches_up_inside_the_window():
    assert due_slots(cfg(), State(), at(14, 30)) == ["09:00"]


def test_too_late_is_skipped_rather_than_posted_at_midnight():
    assert "09:00" not in due_slots(cfg(), State(), at(23, 0))


def test_already_posted_slot_is_not_due():
    state = State()
    state.add(posted("09:00"))
    assert due_slots(cfg(), state, at(10, 0)) == []


def test_both_slots_can_be_due_together_after_an_outage():
    assert due_slots(cfg(catch_up_hours=24), State(), at(18, 0)) == ["09:00", "17:30"]


def test_slot_time_keeps_the_date_and_zone():
    moment = slot_time(at(13, 45), "09:00")
    assert (moment.hour, moment.minute, moment.date()) == (9, 0, at(13, 45).date())


def test_cron_lines_cover_winter_and_summer_offsets():
    lines = cron_lines(cfg(posts_per_day=1, post_times=["09:00"]), year=2026)
    assert lines == ["0 16 * * *", "0 17 * * *"]


def test_prepare_window_only_fires_before_the_slot():
    preview_cfg = cfg(mode="preview", preview_minutes=30)
    from agent.schedule import prepare_slots
    assert prepare_slots(preview_cfg, State(), at(8, 0)) == []
    assert prepare_slots(preview_cfg, State(), at(8, 45)) == ["09:00"]
    assert prepare_slots(preview_cfg, State(), at(9, 5)) == []


def test_auto_mode_never_prepares():
    from agent.schedule import prepare_slots
    assert prepare_slots(cfg(mode="auto"), State(), at(8, 45)) == []


def test_preview_mode_adds_earlier_cron_lines():
    lines = cron_lines(cfg(posts_per_day=1, post_times=["09:00"],
                           mode="preview", preview_minutes=30), year=2026)
    assert lines == ["30 15 * * *", "0 16 * * *", "30 16 * * *", "0 17 * * *"]
