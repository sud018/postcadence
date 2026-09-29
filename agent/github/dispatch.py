"""Starting the posting workflow on demand, instead of waiting for GitHub's cron.

GitHub's scheduled events are best-effort. Through late 2026 they have run
anywhere from eighty minutes to six hours behind, which is long enough that a
post can miss its catch-up window entirely and be dropped.

A `workflow_dispatch` is not scheduled - it is delivered like any other API
call, in seconds. So an outside clock that can make one HTTP request replaces
the part of GitHub that is unreliable, and leaves everything else alone.

`workflow_dispatch` is used rather than `repository_dispatch` for one reason:
the fine-grained token it needs is scoped to *Actions: read and write*, which
can only start workflows. `repository_dispatch` would require *Contents: read
and write* - the right to rewrite the repository - for the same job. The token
lives in somebody else's database, so it should be able to do as little as
possible.
"""
from __future__ import annotations

from agent.github import api

WORKFLOW = "post.yml"
ENDPOINT = "/repos/{repo}/actions/workflows/{workflow}/dispatches"

# What the outside scheduler must send. Kept here so the setup page, the docs
# and the test all quote the same thing.
HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": "Bearer YOUR_TOKEN",
    "X-GitHub-Api-Version": "2022-11-28",
    "Content-Type": "application/json",
}


def url(repo: str) -> str:
    """The full address an outside scheduler POSTs to."""
    return api.API + ENDPOINT.format(repo=repo, workflow=WORKFLOW)


def body(branch: str = "main", dry_run: bool = False) -> dict:
    """The JSON an outside scheduler sends.

    `mode: due` means "do whatever is owed right now" - the same thing the
    cron schedule does, so a punctual trigger and a late one behave alike.
    """
    return {"ref": branch, "inputs": {"mode": "due", "dry_run": dry_run}}


def run_now(repo: str, token: str, branch: str = "main", dry_run: bool = False) -> None:
    """Start the workflow from here, to prove the wiring before trusting it.

    GitHub answers 204 with no body and no run id, so there is nothing to
    return: the caller sends the user to the Actions tab to watch it.
    """
    api.call("POST", ENDPOINT.format(repo=repo, workflow=WORKFLOW), token,
             json=body(branch, dry_run))
