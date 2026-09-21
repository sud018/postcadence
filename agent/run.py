"""The daily pipeline: pick a topic, write, format, post, record."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from agent.config import Config
from agent.formatter import format_post
from agent.linkedin.poster import post_text
from agent.secrets_store import get_secret
from agent.state import HistoryEntry, load_state, save_state
from agent.topics import advance, load_topics, pick_topic
from agent.writer import write_post
from agent.linkedin.errors import LinkedInAuthError, LinkedInError

RECENT_COUNT = 3


@dataclass
class RunResult:
    status: str
    topic: str
    text: str = ""
    post_id: str = ""
    reason: str = ""


def today_in(cfg: Config) -> str:
    return datetime.now(ZoneInfo(cfg.timezone)).date().isoformat()


def _recent_topics(state, limit: int = RECENT_COUNT) -> list[str]:
    seen = [h.topic for h in reversed(state.history) if h.status == "posted"]
    return seen[:limit]


def run_once(cfg: Config, slot: str, dry_run: bool = False, force: bool = False) -> RunResult:
    today = today_in(cfg)
    state = load_state()

    if state.already_handled(today, slot) and not force:
        return RunResult(status="skipped", topic="", reason=f"{today} {slot} was already handled")

    pick = pick_topic(load_topics(), state, slot, today)
    raw = write_post(pick, cfg, _recent_topics(state))
    text = format_post(raw, pick.topic)

    if dry_run:
        return RunResult(status="dry-run", topic=pick.topic, text=text)

    token = get_secret("LINKEDIN_ACCESS_TOKEN")
    if not token or not cfg.linkedin_member_id:
        raise LinkedInAuthError("Not connected. Run: python -m agent linkedin connect")

    try:
        post_id = post_text(text, token, cfg.linkedin_member_id)
    except LinkedInError as exc:
        state.add(HistoryEntry(date=today, slot=slot, topic=pick.topic,
                               status="failed", error=str(exc)[:200]))
        save_state(state)
        raise

    state.add(HistoryEntry(date=today, slot=slot, topic=pick.topic,
                           status="posted", post_id=post_id))
    advance(state, pick)
    save_state(state)

    return RunResult(status="posted", topic=pick.topic, text=text, post_id=post_id)
 