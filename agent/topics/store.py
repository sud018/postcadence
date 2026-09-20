"""Where the topic list lives on disk."""
from __future__ import annotations

from pathlib import Path

from agent import paths
from agent.jsonio import read_json, write_json


def load_topics(path: Path = paths.TOPICS_FILE) -> list[str]:
    if not path.exists():
        return []
    data = read_json(path)
    return list(data.get("topics", []))


def save_topics(topics: list[str], path: Path = paths.TOPICS_FILE) -> None:
    write_json(path, {"topics": topics})
