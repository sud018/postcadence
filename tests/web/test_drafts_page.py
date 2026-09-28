"""The Drafts page: write, edit, publish, skip - without touching LinkedIn."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agent import drafts as book
from agent.linkedin.errors import LinkedInError
from agent.state import load_state
from agent.topics.picker import Pick
from web.app import app
from web.routers import drafts as page

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Never call an LLM or LinkedIn from a test."""
    monkeypatch.setattr(page.run, "compose",
                        lambda cfg, slot, state=None: (Pick("Gamma topic", False, 2), "Written text"))
    monkeypatch.setattr(page, "get_secret", lambda name: "token")


def seed(**kw) -> book.Draft:
    fields = {"date": "2026-09-28", "slot": "09:00", "topic": "Gamma topic",
              "text": "Draft text", "topic_index": 2}
    fields.update(kw)
    return book.add(book.Draft(**fields))


def test_empty_page_invites_you_to_write():
    body = client.get("/drafts").text
    assert "No drafts yet" in body


def test_new_draft_is_written_and_listed():
    client.post("/drafts/new", data={"slot": "09:00"}, follow_redirects=False)
    assert [d.text for d in book.load_drafts()] == ["Written text"]
    assert "Written text" in client.get("/drafts").text


def test_writing_a_draft_does_not_move_the_topic_bookmark():
    before = load_state().next_topic_index
    client.post("/drafts/new", data={"slot": "09:00"}, follow_redirects=False)
    assert load_state().next_topic_index == before


def test_save_edit_keeps_your_words():
    draft = seed()
    client.post(f"/drafts/{draft.id}/save", data={"text": "My own words"}, follow_redirects=False)
    assert book.find(draft.id).text == "My own words"


def test_empty_edit_is_refused():
    draft = seed()
    response = client.post(f"/drafts/{draft.id}/save", data={"text": "   "}, follow_redirects=False)
    assert "error=" in response.headers["location"]
    assert book.find(draft.id).text == "Draft text"


def test_too_long_edit_is_refused():
    draft = seed()
    client.post(f"/drafts/{draft.id}/save", data={"text": "x" * 3001}, follow_redirects=False)
    assert book.find(draft.id).text == "Draft text"


def test_rewrite_replaces_the_text():
    draft = seed()
    client.post(f"/drafts/{draft.id}/rewrite", follow_redirects=False)
    assert book.find(draft.id).text == "Written text"


def test_posting_publishes_advances_and_clears_the_draft(monkeypatch):
    sent = {}

    def fake_publish(cfg, pick, slot, text, date):
        sent["text"] = text
        return "urn:li:share:1"

    monkeypatch.setattr(page.run, "publish", fake_publish)

    draft = seed()
    response = client.post(f"/drafts/{draft.id}/post", follow_redirects=False)

    assert sent["text"] == "Draft text"
    assert "posted=urn" in response.headers["location"].replace("%3A", ":")
    assert book.find(draft.id) is None


def test_a_failed_post_keeps_the_draft(monkeypatch):
    def boom(*args, **kwargs):
        raise LinkedInError("LinkedIn said no")

    monkeypatch.setattr(page.run, "publish", boom)
    draft = seed()
    response = client.post(f"/drafts/{draft.id}/post", follow_redirects=False)

    assert "error=" in response.headers["location"]
    assert book.find(draft.id) is not None


def test_skip_records_the_slot_so_nothing_posts_for_it():
    draft = seed()
    client.post(f"/drafts/{draft.id}/skip", follow_redirects=False)

    state = load_state()
    assert state.already_handled("2026-09-28", "09:00") is True
    assert book.find(draft.id) is None


def test_discard_leaves_no_history():
    draft = seed()
    client.post(f"/drafts/{draft.id}/discard", follow_redirects=False)
    assert load_state().history == []
    assert book.find(draft.id) is None


def test_actions_on_a_missing_draft_say_so():
    response = client.post("/drafts/nope/post", follow_redirects=False)
    assert "error=" in response.headers["location"]


def test_posting_is_off_until_linkedin_is_connected(monkeypatch):
    monkeypatch.setattr(page, "get_secret", lambda name: "")
    seed()
    body = client.get("/drafts").text
    assert "LinkedIn is not connected" in body
    assert "disabled" in body
