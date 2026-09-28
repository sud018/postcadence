"""Drafts written but not yet published, waiting for your approval.

This is the local twin of agent/preview.py. Preview mode opens a GitHub Issue
because nobody is at the keyboard when Actions runs; here you are at the
keyboard, so the draft just lives in data/drafts.json until you decide.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent import paths
from agent.jsonio import read_json, write_json
from agent.topics.picker import Pick


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Draft:
    """One unpublished post. Everything needed to publish it later is here."""

    date: str           # local date it was written for, "YYYY-MM-DD"
    slot: str           # scheduled time it belongs to, "HH:MM"
    topic: str
    text: str
    topic_index: int = 0     # where the topic came from in the list
    is_repeat: bool = False  # True when the list ran out and we reused a topic
    id: str = field(default_factory=lambda: uuid4().hex[:8])
    created_at: str = field(default_factory=_now)

    @property
    def pick(self) -> Pick:
        """Rebuild the Pick, so advance() can move the bookmark on publish."""
        return Pick(topic=self.topic, is_repeat=self.is_repeat, index=self.topic_index)


def load_drafts(path: Path | None = None) -> list[Draft]:
    path = path or paths.DRAFTS_FILE
    if not path.exists():
        return []
    return [Draft(**d) for d in read_json(path).get("drafts", [])]


def save_drafts(drafts: list[Draft], path: Path | None = None) -> None:
    write_json(path or paths.DRAFTS_FILE, {"drafts": [asdict(d) for d in drafts]})


def add(draft: Draft, path: Path | None = None) -> Draft:
    drafts = load_drafts(path)
    drafts.append(draft)
    save_drafts(drafts, path)
    return draft


def find(draft_id: str, path: Path | None = None) -> Draft | None:
    return next((d for d in load_drafts(path) if d.id == draft_id), None)


def remove(draft_id: str, path: Path | None = None) -> bool:
    drafts = load_drafts(path)
    kept = [d for d in drafts if d.id != draft_id]
    if len(kept) == len(drafts):
        return False
    save_drafts(kept, path)
    return True


def set_text(draft_id: str, text: str, path: Path | None = None) -> Draft | None:
    """Save your edit. Returns the updated draft, or None if it is gone."""
    drafts = load_drafts(path)
    for draft in drafts:
        if draft.id == draft_id:
            draft.text = text.strip()
            save_drafts(drafts, path)
            return draft
    return None
