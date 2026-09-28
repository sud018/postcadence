from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent.config import load_config
from web import workflow
from web.app import app
from web.workflow import current_cron

client = TestClient(app)

WORKFLOW = '''name: Post to LinkedIn
on:
  schedule:
    - cron: "0 16 * * *"
  workflow_dispatch:
jobs: {}
'''


@pytest.fixture(autouse=True)
def fake_workflow(tmp_path, monkeypatch):
    path = tmp_path / "post.yml"
    path.write_text(WORKFLOW, encoding="utf-8")
    monkeypatch.setattr(workflow, "workflow_path", lambda: path)
    return path


def test_page_shows_current_times():
    assert 'value="09:00"' in client.get("/setup/schedule").text


def test_saving_updates_config_and_workflow(fake_workflow: Path):
    response = client.post("/setup/schedule", data={
        "post_times": ["17:30", "09:00"], "timezone": "Asia/Kolkata", "mode": "auto",
        "preview_minutes": "30", "preview_timeout_action": "post", "catch_up_hours": "6"})

    assert "Saved" in response.text
    cfg = load_config()
    assert cfg.post_times == ["09:00", "17:30"] and cfg.posts_per_day == 2
    assert current_cron(fake_workflow.read_text()) == ["30 3 * * *", "0 12 * * *"]


def test_invalid_input_is_shown_and_nothing_is_written(fake_workflow: Path):
    before = fake_workflow.read_text()
    response = client.post("/setup/schedule", data={
        "post_times": ["09:00"], "timezone": "Mars/Olympus", "mode": "auto",
        "preview_minutes": "30", "preview_timeout_action": "post", "catch_up_hours": "6"})

    assert "timezone" in response.text
    assert fake_workflow.read_text() == before
    assert load_config().timezone != "Mars/Olympus"


def test_duplicate_times_collapse_to_one(fake_workflow: Path):
    client.post("/setup/schedule", data={
        "post_times": ["09:00", "09:00"], "timezone": "Asia/Kolkata", "mode": "auto",
        "preview_minutes": "30", "preview_timeout_action": "post", "catch_up_hours": "6"})
    assert load_config().post_times == ["09:00"]
