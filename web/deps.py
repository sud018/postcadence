"""Loaders every page needs, in one place."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agent.config import Config, load_config
from agent.schedule import local_now
from agent.state import State, load_state
from agent.status import counts, next_run, post_link, recent, streak, token_days, until
from agent.topics import load_topics


@dataclass
class Snapshot:
    """Everything the dashboard needs, gathered once per request."""

    cfg: Config
    state: State
    topics: list[str]
    now: datetime
    next_slot: str
    next_at: datetime
    countdown: str
    topics_left: int
    days_of_content: float
    token_days: int | None
    streak: int
    tally: dict[str, int]
    recent: list

    @property
    def posted(self) -> int:
        return self.tally.get("posted", 0)

    @property
    def failed(self) -> int:
        return self.tally.get("failed", 0)

    @property
    def success_rate(self) -> int:
        attempts = self.posted + self.failed
        return round(100 * self.posted / attempts) if attempts else 100


def snapshot() -> Snapshot:
    cfg = load_config()
    state = load_state()
    topics = load_topics()
    now = local_now(cfg)
    slot, at = next_run(cfg, now)
    left = max(0, len(topics) - state.next_topic_index)

    return Snapshot(
        cfg=cfg,
        state=state,
        topics=topics,
        now=now,
        next_slot=slot,
        next_at=at,
        countdown=until(at, now),
        topics_left=left,
        days_of_content=round(left / max(1, cfg.posts_per_day), 1),
        token_days=token_days(cfg),
        streak=streak(state, now.date().isoformat()),
        tally=counts(state),
        recent=recent(state, limit=8),
    )


def link_for(entry) -> str:
    return post_link(entry)
