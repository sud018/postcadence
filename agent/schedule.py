"""Work out which post slots are due right now, in the user's timezone."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from agent.config import Config
from agent.state import State


def local_now(cfg: Config) -> datetime:
    """The current time where the user lives, not where the server lives."""
    return datetime.now(ZoneInfo(cfg.timezone))

def slot_time(now: datetime, slot: str):
    """Today's date at the slot's clock time, in the same timezone as `now`."""
    hour, minute = (int(part) for part in slot.split(":"))
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

def occurrences(now: datetime, slot: str) -> list[datetime]:
    """Today's and yesterday's occurrence of this clock time.

    Yesterday's matters: an evening slot whose catch-up window runs past
    midnight is still owed a post, and looking only at today's date would
    quietly abandon it the moment the clock ticks over.
    """
    today = slot_time(now, slot)
    return [today, today - timedelta(days=1)]


def due_slots(cfg: Config, state: State, now: datetime | None = None) -> list[tuple[str, str]]:
    """(date, slot) pairs to act on: the time has passed, the catch-up window
    is still open, and nothing has been posted or skipped for them yet."""
    now = now or local_now(cfg)
    window = timedelta(hours=cfg.catch_up_hours)

    due = []
    for slot in cfg.post_times:
        for scheduled in occurrences(now, slot):
            if now < scheduled:
                continue                  # not time yet
            if now - scheduled > window:
                continue                  # too late; skip rather than post at 3am
            date = scheduled.date().isoformat()
            if state.already_handled(date, slot):
                continue                  # already done
            due.append((date, slot))
    return sorted(due)

def prepare_slots(cfg: Config, state: State,
                  now: datetime | None = None) -> list[tuple[str, str]]:
    """Slots that need a draft written now.

    From `preview_minutes` before the slot until the catch-up window closes -
    deliberately wide. GitHub regularly starts a scheduled run an hour or more
    late, and a draft that can only be written inside a 30-minute window is a
    draft that often never gets written at all.

    Writing the draft late is fine: the review clock starts when the issue is
    opened, not when the slot was supposed to be. prepare_preview() will not
    open a second issue if one is already there.
    """
    if cfg.mode != "preview":
        return []

    now = now or local_now(cfg)
    lead = timedelta(minutes=cfg.preview_minutes)
    window = timedelta(hours=cfg.catch_up_hours)

    ready = []
    for slot in cfg.post_times:
        for scheduled in occurrences(now, slot):
            if now < scheduled - lead:
                continue                  # still too early to write it
            if now - scheduled > window:
                continue                  # too late to bother; the day is gone
            date = scheduled.date().isoformat()
            if state.already_handled(date, slot):
                continue
            ready.append((date, slot))
    return sorted(ready)

def cron_lines(cfg: Config, year: int | None = None) -> list[str]:
    """UTC cron lines covering each slot in both winter and summer offsets.

    Cron has no idea about timezones or daylight saving, so we emit one line
    per distinct UTC time and let due_slots() decide if a run should act.
    """
    tz = ZoneInfo(cfg.timezone)
    year = year or datetime.now(tz).year
    times: set[tuple[int, int]] = set()

    for slot in cfg.post_times:
        hour, minute = (int(part) for part in slot.split(":"))
        for month, day in ((1, 15), (7, 15)):          # a winter and a summer date
            local = datetime(year, month, day, hour, minute, tzinfo=tz)
            times.add(_utc_hm(local))
            if cfg.mode == "preview":
                times.add(_utc_hm(local - timedelta(minutes=cfg.preview_minutes)))

    return [f"{minute} {hour} * * *" for hour, minute in sorted(times)]

def _utc_hm(moment: datetime) -> tuple[int, int]:
    utc = moment.astimezone(ZoneInfo("UTC"))
    return utc.hour, utc.minute
