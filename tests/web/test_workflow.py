import pytest

from agent.config import Config
from web.workflow import WorkflowError, apply, current_cron, rewrite_cron

ORIGINAL = '''name: Post to LinkedIn

on:
  schedule:
    - cron: "30 15 * * *"
    - cron: "0 16 * * *"

  workflow_dispatch:
    inputs:
      slot:
        default: ""

jobs:
  post:
    runs-on: ubuntu-latest
'''


def test_replaces_the_cron_lines_and_nothing_else():
    out = rewrite_cron(ORIGINAL, ["0 8 * * *", "0 9 * * *"])
    assert current_cron(out) == ["0 8 * * *", "0 9 * * *"]
    assert "workflow_dispatch:" in out and "runs-on: ubuntu-latest" in out
    assert out.count("schedule:") == 1


def test_keeps_the_existing_indentation():
    out = rewrite_cron(ORIGINAL, ["0 8 * * *"])
    assert '    - cron: "0 8 * * *"' in out


def test_running_twice_gives_the_same_file():
    once = rewrite_cron(ORIGINAL, ["0 8 * * *"])
    assert rewrite_cron(once, ["0 8 * * *"]) == once


def test_adds_a_schedule_block_when_there_is_none():
    no_schedule = ORIGINAL.replace(
        '  schedule:\n    - cron: "30 15 * * *"\n    - cron: "0 16 * * *"\n\n', "")
    out = rewrite_cron(no_schedule, ["0 8 * * *"])
    assert current_cron(out) == ["0 8 * * *"]
    assert "workflow_dispatch:" in out


def test_refuses_a_file_without_on():
    with pytest.raises(WorkflowError, match="on:"):
        rewrite_cron("name: x\njobs: {}\n", ["0 8 * * *"])


def test_apply_writes_the_lines_for_the_config(tmp_path):
    path = tmp_path / "post.yml"
    path.write_text(ORIGINAL, encoding="utf-8")
    cfg = Config(post_times=["09:00"], timezone="Asia/Kolkata", mode="auto")

    lines, changed = apply(cfg, path)

    assert changed and lines == ["30 3 * * *"]
    assert current_cron(path.read_text(encoding="utf-8")) == ["30 3 * * *"]


def test_apply_reports_no_change_when_already_in_step(tmp_path):
    path = tmp_path / "post.yml"
    path.write_text(ORIGINAL, encoding="utf-8")
    cfg = Config(post_times=["09:00"], timezone="Asia/Kolkata", mode="auto")
    apply(cfg, path)
    assert apply(cfg, path)[1] is False
