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
from agent.state import HistoryEntry, State, load_state

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


def key(entry: HistoryEntry) -> tuple[str, str, str]:
    """What makes one history entry the same entry as another.

    created_at is stamped when the entry is made, so two runs on two machines
    never collide - and the same entry copied between them always matches.
    """
    return (entry.date, entry.slot, entry.created_at)


def merge(mine: State, theirs: State) -> State:
    """Both histories, no duplicates, oldest first.

    Neither side is the loser: GitHub knows about its scheduled posts, this
    machine knows about the ones you approved by hand, and both really happened.
    """
    entries = {key(e): e for e in theirs.history}
    entries.update({key(e): e for e in mine.history})

    return State(
        # whoever is further through the topic list has used more of it
        next_topic_index=max(mine.next_topic_index, theirs.next_topic_index),
        history=sorted(entries.values(), key=key),
    )


def unpushed_runs(repo: str, token: str) -> int:
    """How many history entries this machine has that GitHub has not seen."""
    remote, _ = api.get_file(repo, STATE_PATH, token)
    theirs = State.from_dict(json.loads(remote)) if remote else State()
    known = {key(e) for e in theirs.history}
    return sum(1 for e in load_state().history if key(e) not in known)


def push_state(repo: str, token: str) -> int:
    """Send this machine's posts up, keeping GitHub's. Returns how many were new.

    This is the one exception to "state only flows down": a post you approved
    in the app really happened, and until GitHub knows, its scheduled run will
    publish that slot all over again.
    """
    remote, _ = api.get_file(repo, STATE_PATH, token)
    theirs = State.from_dict(json.loads(remote)) if remote else State()
    mine = load_state()

    merged = merge(mine, theirs)
    added = len(merged.history) - len(theirs.history)
    if added == 0 and merged.next_topic_index == theirs.next_topic_index:
        return 0

    text = json.dumps(merged.to_dict(), indent=2, ensure_ascii=False) + "\n"
    api.put_file(repo, STATE_PATH, text, "chore: record posts made in the app", token)
    write_json(paths.STATE_FILE, merged.to_dict())      # both sides now agree
    return added


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
