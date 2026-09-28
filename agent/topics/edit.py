"""Changing the topic list, with the bookmark kept honest.

Pure functions: lists and an index in, lists and an index out. No files.
"""
from __future__ import annotations

from agent.topics.loader import TopicError


def merge(existing: list[str], incoming: list[str]) -> list[str]:
    """Append topics that are not already present, ignoring case."""
    seen = {topic.lower() for topic in existing}
    added = []
    for topic in incoming:
        if topic.lower() in seen:
            continue
        seen.add(topic.lower())
        added.append(topic)
    return existing + added


def remove_at(topics: list[str], index: int, bookmark: int) -> tuple[list[str], int]:
    """Delete one topic. If it was already used, the bookmark moves back with it."""
    if not 0 <= index < len(topics):
        raise TopicError(f"No topic at position {index}.")

    remaining = topics[:index] + topics[index + 1:]
    if index < bookmark:
        bookmark -= 1
    return remaining, max(0, min(bookmark, len(remaining)))


def move(topics: list[str], index: int, delta: int, bookmark: int) -> tuple[list[str], int]:
    """Swap a topic with its neighbour. The bookmark counts positions, so it stays put."""
    target = index + delta
    if not 0 <= index < len(topics):
        raise TopicError(f"No topic at position {index}.")
    if not 0 <= target < len(topics):
        return topics, bookmark            # already at an end; nothing to do

    reordered = topics[:]
    reordered[index], reordered[target] = reordered[target], reordered[index]
    return reordered, bookmark


def rename_at(topics: list[str], index: int, text: str) -> list[str]:
    text = text.strip()
    if not 0 <= index < len(topics):
        raise TopicError(f"No topic at position {index}.")
    if len(text) < 3:
        raise TopicError("A topic needs at least 3 characters.")

    renamed = topics[:]
    renamed[index] = text
    return renamed
