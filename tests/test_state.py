import pytest

from agent.state import HistoryEntry, State, load_state, save_state


def test_missing_file_gives_empty_state(tmp_path):
    state = load_state(tmp_path / "nope.json")
    assert state.next_topic_index == 0 and state.history == []


def test_round_trip(tmp_path):
    path = tmp_path / "state.json"
    state = State(next_topic_index=3)
    state.add(HistoryEntry(date="2026-09-17", slot="09:00", topic="AI agents", status="posted"))
    save_state(state, path)

    loaded = load_state(path)
    assert loaded.next_topic_index == 3
    assert loaded.history[0].topic == "AI agents"


def test_already_handled():
    state = State()
    state.add(HistoryEntry(date="2026-09-17", slot="09:00", topic="x", status="failed"))
    assert not state.already_handled("2026-09-17", "09:00")  # failed -> retry allowed
    state.add(HistoryEntry(date="2026-09-17", slot="09:00", topic="x", status="posted"))
    assert state.already_handled("2026-09-17", "09:00")


def test_invalid_status():
    with pytest.raises(ValueError):
        State().add(HistoryEntry(date="d", slot="s", topic="t", status="oops"))
