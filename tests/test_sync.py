"""Sync: settings flow up, post history flows down - never the other way."""
from __future__ import annotations

import json

import pytest

from agent import paths
from agent.github import sync
from agent.state import HistoryEntry, State, load_state, save_state


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    monkeypatch.setattr(paths, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(paths, "STATE_FILE", tmp_path / "data" / "state.json")
    (tmp_path / "data").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "data" / "config.json").write_text('{"tone": "casual"}', encoding="utf-8")
    (tmp_path / "data" / "topics.json").write_text('{"topics": ["a"]}', encoding="utf-8")
    (tmp_path / ".github" / "workflows" / "post.yml").write_text("on: {}\n", encoding="utf-8")


def remote(files: dict[str, str]):
    """A fake get_file that answers from a dict, like a repo would."""
    return lambda repo, path, token: (files.get(path, ""), "sha" if path in files else "")


def history(n: int) -> State:
    return State(history=[HistoryEntry(date="2026-09-01", slot="09:00", topic=f"t{i}", status="posted")
                          for i in range(n)])


def test_line_endings_do_not_count_as_a_change():
    assert sync.same_text("a\r\nb\r\n", "a\nb")


def test_real_differences_do():
    assert not sync.same_text("tone: casual", "tone: professional")


def test_compare_reports_each_file(monkeypatch):
    monkeypatch.setattr(sync.api, "get_file", remote({
        "data/config.json": '{"tone": "casual"}',            # same
        "data/topics.json": '{"topics": ["a", "b"]}',        # changed
    }))                                                       # post.yml missing

    status = {f.path: f.status for f in sync.compare("me/agent", "t")}
    assert status == {
        "data/config.json": "same",
        "data/topics.json": "changed",
        ".github/workflows/post.yml": "missing",
    }


def test_state_is_never_in_the_upload_list():
    assert "data/state.json" not in [path for path, _ in sync.UP]


def test_newer_runs_counts_what_github_has_and_we_do_not(monkeypatch):
    save_state(history(2))
    monkeypatch.setattr(sync.api, "get_file",
                        remote({"data/state.json": json.dumps(history(5).to_dict())}))
    assert sync.newer_runs("me/agent", "t") == 3


def test_being_ahead_of_github_is_not_negative(monkeypatch):
    save_state(history(4))
    monkeypatch.setattr(sync.api, "get_file",
                        remote({"data/state.json": json.dumps(history(1).to_dict())}))
    assert sync.newer_runs("me/agent", "t") == 0


def test_pull_state_replaces_the_local_copy(monkeypatch):
    save_state(history(1))
    monkeypatch.setattr(sync.api, "get_file",
                        remote({"data/state.json": json.dumps(history(4).to_dict())}))

    assert sync.pull_state("me/agent", "t") == 4
    assert len(load_state().history) == 4


def test_pull_with_no_remote_state_changes_nothing(monkeypatch):
    save_state(history(2))
    monkeypatch.setattr(sync.api, "get_file", remote({}))
    assert sync.pull_state("me/agent", "t") == 0
    assert len(load_state().history) == 2
