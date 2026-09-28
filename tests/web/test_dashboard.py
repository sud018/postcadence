from fastapi.testclient import TestClient

from web.app import app

client = TestClient(app)


def test_dashboard_renders():
    response = client.get("/")
    assert response.status_code == 200
    assert "Next post" in response.text


def test_dashboard_shows_the_next_slot():
    from agent.config import load_config
    response = client.get("/")
    assert load_config().post_times[0] in response.text


def test_static_css_is_served():
    assert client.get("/static/css/app.css").status_code == 200
