import pytest

from agent.topics.edit import merge, move, remove_at, rename_at
from agent.topics.loader import TopicError

TOPICS = ["A", "B", "C", "D"]


def test_merge_adds_only_new_topics():
    assert merge(["A", "B"], ["b", "C"]) == ["A", "B", "C"]


def test_merge_keeps_order_and_ignores_internal_duplicates():
    assert merge([], ["X", "x", "Y"]) == ["X", "Y"]


def test_removing_a_used_topic_moves_the_bookmark_back():
    topics, bookmark = remove_at(TOPICS, 0, 2)      # "A" was used
    assert topics == ["B", "C", "D"] and bookmark == 1


def test_removing_a_queued_topic_leaves_the_bookmark_alone():
    topics, bookmark = remove_at(TOPICS, 3, 2)      # "D" was queued
    assert topics == ["A", "B", "C"] and bookmark == 2


def test_bookmark_never_points_past_the_end():
    topics, bookmark = remove_at(["A"], 0, 1)
    assert topics == [] and bookmark == 0


def test_removing_a_missing_position_raises():
    with pytest.raises(TopicError, match="No topic at position"):
        remove_at(TOPICS, 9, 0)


def test_move_swaps_neighbours():
    topics, bookmark = move(TOPICS, 1, +1, 2)
    assert topics == ["A", "C", "B", "D"] and bookmark == 2


def test_move_at_the_edge_does_nothing():
    assert move(TOPICS, 0, -1, 0) == (TOPICS, 0)


def test_rename_replaces_one_topic():
    assert rename_at(TOPICS, 2, "  New text  ") == ["A", "B", "New text", "D"]


def test_rename_rejects_something_too_short():
    with pytest.raises(TopicError, match="3 characters"):
        rename_at(TOPICS, 0, "ab")
