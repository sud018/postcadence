"""Decide which topic a given post slot should use."""
from __future__ import annotations

from dataclasses import dataclass

from agent.state import State
from agent.topics.loader import TopicError


@dataclass
class Pick:
    topic: str
    is_repeat: bool
    index: int

def _last_posted_topic(state: State, slot: str, today: str):
    """The topic last published in this slot on an earlier day."""
    for entry in reversed(state.history):
        if entry.status=="posted" and entry.slot==slot and entry.date!=today:
            return entry.topic
    for entry in reversed(state.history):
        if entry.status=="posted" and entry.date!=today:
            return entry.topic
    return ""

def pick_topic(topics: list[str], state: State, slot: str, today: str):
    """Next unused topic if there is one, otherwise repeat the previous day's."""
    index = state.next_topic_index

    if 0<=index<len(topics):
        return Pick(topics[index], False, index)

    previous = _last_posted_topic(state, slot, today)
    if previous:
        return Pick(topic=previous, is_repeat=True, index=index)

    if topics:
        return Pick(topic=topics[-1], is_repeat=True, index=index)

    raise TopicError("No topics configured. Run: python -m agent topics add --file <path>")


def advance(state: State, pick: Pick) -> None:
    """Move to the next topic - only after a fresh topic was actually used."""
    if not pick.is_repeat:
        state.next_topic_index = pick.index + 1
