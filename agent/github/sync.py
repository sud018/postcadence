"""Is this machine and the GitHub repository saying the same thing?

Two directions, two owners:
  - config, topics, post.yml: YOU change these here, so they flow UP.
  - state.json: the WORKFLOW changes it on GitHub, so it flows DOWN.

Getting the direction wrong is how a real post gets forgotten, so each file
has exactly one owner and the code never pushes the other way.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from agent import paths
from agent.github import api
from agent.jsonio import write_json
from agent.state import State, load_state

# (repo path, what it is) - pushed from here to GitHub
UP = (
    ("data/config.json", "your settings"),
    ("data/topics.json", "your topic list"),
    (".github/workflows/post.yml", "the schedule"),
)
STATE_PATH = "data/state.json"


@dataclass
class FileStatus:
    path: str
    label: str
    status: str        # same / changed / missing


def local_text(path: str) -> str:
    """Read one synced file from this machine ('' when it does not exist)."""
    target = paths.ROOT / path
    if path.startswith("data/"):
        target = paths.DATA_DIR / path.split("/", 1)[1]
    return target.read_text(encoding="utf-8") if target.exists() else ""


def same_text(a: str, b: str) -> bool:
    """Equal apart from line endings - Windows and GitHub disagree about those."""
    return a.replace("\r\n", "\n").strip() == b.replace("\r\n", "\n").strip()


def compare(repo: str, token: str) -> list[FileStatus]:
    """Which of the files you own still need pushing."""
    result = []
    for path, label in UP:
        remote, _ = api.get_file(repo, path, token)
        if not remote:
            status = "missing"
        elif same_text(remote, local_text(path)):
            status = "same"
        else:
            status = "changed"
        result.append(FileStatus(path, label, status))
    return result


def newer_runs(repo: str, token: str) -> int:
    """How many history entries GitHub has that this machine has not seen."""
    remote, _ = api.get_file(repo, STATE_PATH, token)
    if not remote:
        return 0
    theirs = State.from_dict(json.loads(remote))
    return max(0, len(theirs.history) - len(load_state().history))


def pull_state(repo: str, token: str) -> int:
    """Replace the local state with GitHub's. Returns how many entries it holds.

    Safe because the workflow is the only writer of state that matters: every
    real post was recorded there first.
    """
    remote, _ = api.get_file(repo, STATE_PATH, token)
    if not remote:
        return 0
    theirs = State.from_dict(json.loads(remote))
    write_json(paths.STATE_FILE, theirs.to_dict())
    return len(theirs.history)
