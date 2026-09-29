"""The daily pipeline: pick a topic, write, format, post, record."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from agent import preview
from agent.config import Config
from agent.formatter import format_post
from agent.linkedin.errors import LinkedInAuthError, LinkedInError
from agent.linkedin.poster import post_text
from agent.preview import PreviewError
from agent.secrets_store import get_secret
from agent.state import HistoryEntry, State, load_state, save_state
from agent.topics import Pick, advance, load_topics, pick_topic
from agent.writer import write_post

RECENT_COUNT = 3


@dataclass
class RunResult:
    status: str        # posted / skipped / failed / dry-run
    topic: str
    text: str = ""
    post_id: str = ""
    reason: str = ""


def today_in(cfg: Config) -> str:
    return datetime.now(ZoneInfo(cfg.timezone)).date().isoformat()


def _recent_topics(state, limit: int = RECENT_COUNT) -> list[str]:
    seen = [h.topic for h in reversed(state.history) if h.status == "posted"]
    return seen[:limit]


NOT_CONNECTED = ("Not connected to LinkedIn. Connect it on the Setup page, "
                 "or run: python -m agent linkedin connect")


def compose(cfg: Config, slot: str, state: State | None = None) -> tuple[Pick, str]:
    """Pick a topic and write the post - no posting, no state changes.

    Shared by the scheduled run, preview mode and the Drafts page, so all three
    produce exactly the same text for a slot.
    """
    state = state if state is not None else load_state()
    pick = pick_topic(load_topics(), state, slot, today_in(cfg))
    raw = write_post(pick, cfg, _recent_topics(state))
    return pick, format_post(raw, pick.topic)


def publish(cfg: Config, pick: Pick, slot: str, text: str, date: str = "") -> str:
    """Send the text to LinkedIn and record what happened. Returns the post id.

    State is reloaded here rather than passed in, because minutes can pass
    between writing a draft and approving it.
    """
    today = date or today_in(cfg)
    state = load_state()

    token = get_secret("LINKEDIN_ACCESS_TOKEN")
    if not token or not cfg.linkedin_member_id:
        raise LinkedInAuthError(NOT_CONNECTED)

    try:
        post_id = post_text(text, token, cfg.linkedin_member_id)
    except LinkedInError as exc:
        state.add(HistoryEntry(date=today, slot=slot, topic=pick.topic,
                               status="failed", error=str(exc)[:200]))
        save_state(state)
        raise

    state.add(HistoryEntry(date=today, slot=slot, topic=pick.topic,
                           status="posted", post_id=post_id))
    advance(state, pick)          # only moves on for a fresh topic
    save_state(state)
    return post_id


def record_failure(cfg: Config, slot: str, reason: str, topic: str = "", date: str = "") -> None:
    """Leave a trace when something goes wrong before a post is even attempted.

    Without this, a draft that could not be written and a draft issue that could
    not be opened both look exactly like a quiet day: no post, no history, no
    warning anywhere.
    """
    state = load_state()
    today = date or today_in(cfg)
    reason = reason[:200]

    if state.has_failure(today, slot, reason):
        return                              # already said so; do not repeat it

    state.add(HistoryEntry(date=today, slot=slot, topic=topic, status="failed", error=reason))
    save_state(state)


def record_skip(cfg: Config, pick: Pick, slot: str, date: str = "") -> None:
    """Remember that this slot was deliberately passed over."""
    state = load_state()
    state.add(HistoryEntry(date=date or today_in(cfg), slot=slot, topic=pick.topic, status="skipped"))
    save_state(state)


def run_once(cfg: Config, slot: str, dry_run: bool = False, force: bool = False) -> RunResult:
    today = today_in(cfg)
    state = load_state()

    if state.already_handled(today, slot) and not force:
        return RunResult(status="skipped", topic="", reason=f"{today} {slot} was already handled")

    try:
        pick, text = compose(cfg, slot, state)
    except Exception as exc:                # the writer failed: say so, then raise
        record_failure(cfg, slot, f"Could not write the post: {exc}")
        raise

    if dry_run:
        return RunResult(status="dry-run", topic=pick.topic, text=text)

    post_id = publish(cfg, pick, slot, text, today)
    return RunResult(status="posted", topic=pick.topic, text=text, post_id=post_id)


def prepare_preview(cfg: Config, slot: str) -> RunResult:
    """Write a draft and open it as a GitHub Issue for review."""
    today = today_in(cfg)
    state = load_state()

    if preview.open_draft(today, slot) is not None:
        return RunResult(status="skipped", topic="", reason=f"a draft for {slot} is already open")

    try:
        pick, text = compose(cfg, slot, state)
    except Exception as exc:
        record_failure(cfg, slot, f"Could not write the post: {exc}", date=today)
        raise

    try:
        number = preview.create_draft(today, slot, pick.topic, text,
                                      cfg.preview_timeout_action, cfg.preview_minutes)
    except PreviewError as exc:
        record_failure(cfg, slot, f"Could not open the draft issue: {exc}", pick.topic, today)
        raise

    return RunResult(status="drafted", topic=pick.topic, text=text, reason=f"issue #{number}")


def decide_preview(cfg: Config, slot: str) -> RunResult:
    """Act on the open draft: publish it, publish your edit, or skip it."""
    today = today_in(cfg)
    state = load_state()

    if state.already_handled(today, slot):
        return RunResult(status="skipped", topic="", reason=f"{today} {slot} was already handled")

    draft = preview.open_draft(today, slot)
    if draft is None:
        # The 08:30 run should have opened one. Something went wrong then, and
        # staying quiet about it is how a day goes by with no post at all.
        reason = "No draft issue was found, so there was nothing to publish."
        record_failure(cfg, slot, reason, date=today)
        return RunResult(status="failed", topic="", reason=reason)

    decision = draft.decision
    if decision == "none":
        # Nobody has answered yet. Give them the full review window, counted
        # from when the issue opened - a draft written late still gets its
        # 30 minutes, instead of being published the second it appears.
        waited = draft.minutes_open()
        if waited < cfg.preview_minutes:
            left = int(cfg.preview_minutes - waited)
            return RunResult(status="waiting", topic="",
                             reason=f"draft #{draft.number} has {left} min of review time left")

        decision = "approve" if cfg.preview_timeout_action == "post" else "cancel"

    pick = pick_topic(load_topics(), state, slot, today)

    if decision == "cancel":
        record_skip(cfg, pick, slot, today)
        preview.close_draft(draft.number, "Cancelled - nothing was published.")
        return RunResult(status="skipped", topic=pick.topic, reason="cancelled in the draft issue")

    try:
        post_id = publish(cfg, pick, slot, draft.text, today)
    except LinkedInError as exc:
        preview.close_draft(draft.number, f"Posting failed: {exc}")
        raise

    preview.close_draft(draft.number, f"Published: {post_id}")

    return RunResult(status="posted", topic=pick.topic, text=draft.text, post_id=post_id)
