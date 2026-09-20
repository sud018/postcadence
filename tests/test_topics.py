import pytest

from agent.state import HistoryEntry, State
from agent.topics.loader import TopicError, clean, load_typed
from agent.topics.picker import advance, pick_topic

TOPICS = ["RAG failures", "Vector DBs", "Agent memory"]


def posted(date, slot, topic):
    return HistoryEntry(date=date, slot=slot, topic=topic, status="posted")


def test_clean_strips_bullets_headers_and_duplicates():
    assert clean(["Topic", "1. A topic", "- a TOPIC", "", "x", "Another one"]) == ["A topic", "Another one"]


def test_typed_accepts_semicolons_and_newlines():
    assert load_typed("one thing; two thing\nthree thing") == ["one thing", "two thing", "three thing"]


def test_picks_in_order_and_advances():
    state = State()
    first = pick_topic(TOPICS, state, "09:00", "2026-09-19")
    assert (first.topic, first.is_repeat) == ("RAG failures", False)

    advance(state, first)
    assert state.next_topic_index == 1

    second = pick_topic(TOPICS, state, "17:30", "2026-09-19")
    assert second.topic == "Vector DBs"


def test_repeats_previous_day_same_slot_when_list_runs_out():
    state = State(next_topic_index=len(TOPICS))
    state.add(posted("2026-09-18", "09:00", "Vector DBs"))
    state.add(posted("2026-09-18", "17:30", "Agent memory"))

    pick = pick_topic(TOPICS, state, "09:00", "2026-09-19")
    assert (pick.topic, pick.is_repeat) == ("Vector DBs", True)


def test_repeat_does_not_advance_the_index():
    state = State(next_topic_index=len(TOPICS))
    state.add(posted("2026-09-18", "09:00", "Agent memory"))

    pick = pick_topic(TOPICS, state, "09:00", "2026-09-19")
    advance(state, pick)
    assert state.next_topic_index == len(TOPICS)


def test_falls_back_to_last_topic_when_no_history():
    pick = pick_topic(TOPICS, State(next_topic_index=99), "09:00", "2026-09-19")
    assert (pick.topic, pick.is_repeat) == ("Agent memory", True)


def test_no_topics_at_all_raises():
    with pytest.raises(TopicError, match="No topics configured"):
        pick_topic([], State(), "09:00", "2026-09-19")


def test_ignores_todays_own_posts_when_repeating():
    state = State(next_topic_index=len(TOPICS))
    state.add(posted("2026-09-18", "09:00", "Vector DBs"))
    state.add(posted("2026-09-19", "09:00", "Something today"))

    pick = pick_topic(TOPICS, state, "09:00", "2026-09-19")
    assert pick.topic == "Vector DBs"
