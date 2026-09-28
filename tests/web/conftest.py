"""Web tests run against a throwaway data folder, never your real one."""
import json

import pytest

from agent import paths


@pytest.fixture(autouse=True)
def sandbox_data(tmp_path, monkeypatch):
    """Point every data file at a temp directory for the duration of one test."""
    config = {
        "llm_provider": "openai",
        "timezone": "America/Los_Angeles",
        "posts_per_day": 1,
        "post_times": ["09:00"],
        "mode": "auto",
        "linkedin_member_id": "TEST",
        "linkedin_token_expires": "2026-12-31",
    }
    (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
    (tmp_path / "state.json").write_text('{"next_topic_index": 2, "history": []}', encoding="utf-8")
    (tmp_path / "topics.json").write_text(
        json.dumps({"topics": ["Alpha topic", "Beta topic", "Gamma topic"]}), encoding="utf-8")

    monkeypatch.setattr(paths, "DATA_DIR", tmp_path)
    monkeypatch.setattr(paths, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(paths, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(paths, "TOPICS_FILE", tmp_path / "topics.json")
    yield
