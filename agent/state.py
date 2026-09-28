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
    date: str          # local date, "YYYY-MM-DD"
    slot: str          # scheduled time, "HH:MM"
    topic: str
    status: str
    post_id: str = ""  # LinkedIn post URN once published
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

    def has_failure(self, date: str, slot: str, error: str) -> bool:
        """Have we already complained about exactly this? Stops a repeated
        failure filling the history with the same line every cron tick."""
        return any(
            h.date == date and h.slot == slot and h.status == "failed" and h.error == error
            for h in self.history
        )

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


def load_state(path: Path | None = None) -> State:
    path = path or paths.STATE_FILE
    return State.from_dict(read_json(path)) if path.exists() else State()


def save_state(state: State, path: Path | None = None) -> None:
    write_json(path or paths.STATE_FILE, state.to_dict())
