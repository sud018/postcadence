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

def due_slots(cfg: Config, state: State, now: datetime | None = None) -> list[str]:
    """Slots whose time has passed today, are still within the catch-up
    window, and have not already been posted or skipped."""
    now = now or local_now(cfg)
    today = now.date().isoformat()
    window = timedelta(hours=cfg.catch_up_hours)

    due = []
    for slot in cfg.post_times:
        scheduled = slot_time(now, slot)
        if now < scheduled:
            continue                      # not time yet
        if now - scheduled > window:
            continue                      # too late; skip rather than post at 3am
        if state.already_handled(today, slot):
            continue                      # already done
        due.append(slot)
    return due

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
            utc = local.astimezone(ZoneInfo("UTC"))
            times.add((utc.hour, utc.minute))

    return [f"{minute} {hour} * * *" for hour, minute in sorted(times)]