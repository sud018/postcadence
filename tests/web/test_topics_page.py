from fastapi.testclient import TestClient

from agent.topics import load_topics
from web.app import app

client = TestClient(app)


def test_page_lists_every_topic():
    body = client.get("/topics").text
    assert "Alpha topic" in body and "Gamma topic" in body


def test_add_returns_the_updated_table():
    response = client.post("/topics/add", data={"text": "Delta topic"})
    assert response.status_code == 200
    assert "Delta topic" in response.text
    assert load_topics()[-1] == "Delta topic"


def test_add_ignores_a_duplicate():
    client.post("/topics/add", data={"text": "alpha TOPIC"})
    assert len(load_topics()) == 3


def test_delete_removes_one():
    client.post("/topics/delete", data={"index": "1"})
    assert load_topics() == ["Alpha topic", "Gamma topic"]


def test_move_swaps_two():
    client.post("/topics/move", data={"index": "0", "delta": "1"})
    assert load_topics()[:2] == ["Beta topic", "Alpha topic"]


def test_rename_updates_in_place():
    client.post("/topics/rename", data={"index": "2", "text": "Renamed topic"})
    assert load_topics()[2] == "Renamed topic"


def test_a_bad_index_shows_an_error_not_a_crash():
    response = client.post("/topics/delete", data={"index": "99"})
    assert response.status_code == 200
    assert "No topic at position" in response.text


def test_upload_imports_from_a_csv():
    files = {"file": ("more.csv", b"Imported one\nImported two\n", "text/csv")}
    response = client.post("/topics/upload", files=files)
    assert "Imported one" in response.text
    assert "Imported two" in load_topics()
