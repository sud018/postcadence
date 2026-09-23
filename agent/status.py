"""A single view of what the agent is doing and what it has done."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from agent.config import Config
from agent.schedule import local_now, slot_time
from agent.state import HistoryEntry, State

POST_URL = "https://www.linkedin.com/feed/update/{urn}/"


def next_run(cfg: Config, now: datetime | None = None) -> tuple[str, datetime]:
    """The next slot that will fire, and when - today's if any remain, else tomorrow's first."""
    now = now or local_now(cfg)
    for slot in cfg.post_times:
        scheduled = slot_time(now, slot)
        if scheduled > now:
            return slot, scheduled
    first = cfg.post_times[0]
    return first, slot_time(now, first) + timedelta(days=1)


def until(moment: datetime, now: datetime) -> str:
    """'in 3h 12m', or 'now' if it is due."""
    gap = moment - now
    if gap.total_seconds() <= 0:
        return "now"
    hours, remainder = divmod(int(gap.total_seconds()), 3600)
    return f"in {hours}h {remainder // 60}m" if hours else f"in {remainder // 60}m"


def token_days(cfg: Config) -> int | None:
    if not cfg.linkedin_token_expires:
        return None
    return (date.fromisoformat(cfg.linkedin_token_expires) - date.today()).days


def counts(state: State) -> dict[str, int]:
    tally: dict[str, int] = {}
    for entry in state.history:
        tally[entry.status] = tally.get(entry.status, 0) + 1
    return tally


def recent(state: State, limit: int = 5) -> list[HistoryEntry]:
    return list(reversed(state.history[-limit:]))


def post_link(entry: HistoryEntry) -> str:
    return POST_URL.format(urn=entry.post_id) if entry.post_id else ""
