"""The local draft store: save, edit, publish-and-forget."""
from __future__ import annotations

import pytest

from agent import drafts as book


@pytest.fixture
def path(tmp_path):
    return tmp_path / "drafts.json"


def make(text: str = "Hello", **kw) -> book.Draft:
    fields = {"date": "2026-09-28", "slot": "09:00", "topic": "Testing", "text": text}
    fields.update(kw)
    return book.Draft(**fields)


def test_missing_file_is_an_empty_list(path):
    assert book.load_drafts(path) == []


def test_add_then_load_round_trip(path):
    book.add(make(), path)
    loaded = book.load_drafts(path)
    assert len(loaded) == 1
    assert loaded[0].topic == "Testing"


def test_ids_are_unique(path):
    a = book.add(make("one"), path)
    b = book.add(make("two"), path)
    assert a.id != b.id
    assert len(book.load_drafts(path)) == 2


def test_find_returns_none_for_unknown_id(path):
    book.add(make(), path)
    assert book.find("nope", path) is None


def test_set_text_saves_the_edit_and_trims_it(path):
    draft = book.add(make(), path)
    book.set_text(draft.id, "  edited  ", path)
    assert book.find(draft.id, path).text == "edited"


def test_set_text_on_a_missing_draft_is_none(path):
    assert book.set_text("nope", "x", path) is None


def test_remove_reports_whether_it_removed_anything(path):
    draft = book.add(make(), path)
    assert book.remove(draft.id, path) is True
    assert book.remove(draft.id, path) is False
    assert book.load_drafts(path) == []


def test_pick_is_rebuilt_so_the_bookmark_can_advance(path):
    draft = make(topic_index=4, is_repeat=False)
    assert draft.pick.index == 4
    assert draft.pick.topic == "Testing"
    assert draft.pick.is_repeat is False


def test_repeat_pick_survives_the_round_trip(path):
    book.add(make(topic_index=7, is_repeat=True), path)
    assert book.load_drafts(path)[0].pick.is_repeat is True
