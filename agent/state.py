"""What the agent remembers between runs: topic progress and post history."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from agent import paths
from agent.jsonio import read_json, write_json

STATUSES = ("posted", "failed", "skipped", "pending_preview")


@dataclass
class HistoryEntry:
    date: str
    slot: str
    topic: str
    status: str
    post_id: str = ""
    error: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


@dataclass
class State:
    next_topic_index: int = 0
    history: list[HistoryEntry] = field(default_factory=list)

    def add(self, entry: HistoryEntry) -> None:
        if entry.status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        self.history.append(entry)

    def already_handled(self, date: str, slot: str) -> bool:
        """True if this date+slot was already posted or skipped (so we never double-post)."""
        return any(
            h.date == date and h.slot == slot and h.status in ("posted", "skipped")
            for h in self.history
        )

    def to_dict(self) -> dict:
        return {"next_topic_index": self.next_topic_index,
                "history": [asdict(h) for h in self.history]}

    @classmethod
    def from_dict(cls, data: dict) -> State:
        return cls(
            next_topic_index=int(data.get("next_topic_index", 0)),
            history=[HistoryEntry(**h) for h in data.get("history", [])],
        )


def load_state(path: Path = paths.STATE_FILE) -> State:
    return State.from_dict(read_json(path)) if path.exists() else State()


def save_state(state: State, path: Path = paths.STATE_FILE) -> None:
    write_json(path, state.to_dict())
