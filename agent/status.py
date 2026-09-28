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


def link_for_id(post_id: str) -> str:
    """The public URL of a post, from its LinkedIn id."""
    return POST_URL.format(urn=post_id) if post_id else ""


def post_link(entry: HistoryEntry) -> str:
    return link_for_id(entry.post_id)


def posted_dates(state: State) -> set[str]:
    """Every local date that has at least one published post."""
    return {entry.date for entry in state.history if entry.status == "posted"}


def streak(state: State, today: str) -> int:
    """Consecutive days ending today - or yesterday, since today may not be over."""
    dates = posted_dates(state)
    if not dates:
        return 0

    day = date.fromisoformat(today)
    if day.isoformat() not in dates:
        day -= timedelta(days=1)          # today has not posted yet; that is fine

    count = 0
    while day.isoformat() in dates:
        count += 1
        day -= timedelta(days=1)
    return count
