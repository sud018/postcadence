"""The small slice of the GitHub REST API this app needs."""
from __future__ import annotations

import base64
import re
from pathlib import Path

import requests

from agent import paths
from agent.github.errors import GitHubAuthError, GitHubError

API = "https://api.github.com"
TIMEOUT = 30

# https://github.com/owner/repo.git  and  git@github.com:owner/repo.git
REMOTE = re.compile(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?$")


def call(method: str, path: str, token: str, **kwargs) -> dict | list:
    """One place for headers, timeouts and error messages."""
    response = requests.request(
        method,
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=TIMEOUT,
        **kwargs,
    )

    if response.status_code in (401, 403):
        raise GitHubAuthError(
            f"GitHub refused the token ({response.status_code}). "
            "Reconnect, and make sure the app may read and write this repository."
        )
    if response.status_code >= 300:
        raise GitHubError(f"GitHub {method} {path} failed ({response.status_code}): {response.text[:300]}")

    return response.json() if response.content else {}


def current_user(token: str) -> str:
    """The login name the token belongs to - proof the connection works."""
    return call("GET", "/user", token)["login"]


def repo_from_remote(git_config: Path | None = None) -> str:
    """Read 'owner/repo' out of .git/config, so nobody has to type it.

    Returns "" when this folder is not a git repo, or has no GitHub remote.
    """
    git_config = git_config or paths.ROOT / ".git" / "config"
    if not git_config.exists():
        return ""

    for line in git_config.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line.startswith("url"):
            continue
        match = REMOTE.search(line.split("=", 1)[-1].strip())
        if match:
            return f"{match.group(1)}/{match.group(2)}"
    return ""


def get_file(repo: str, path: str, token: str) -> tuple[str, str]:
    """(text, sha) of a file in the repo. ("", "") when it does not exist yet."""
    try:
        data = call("GET", f"/repos/{repo}/contents/{path}", token)
    except GitHubError as exc:
        if "404" in str(exc):
            return "", ""
        raise
    content = base64.b64decode(data.get("content", "")).decode("utf-8")
    return content, data.get("sha", "")


def put_file(repo: str, path: str, text: str, message: str, token: str) -> str:
    """Create or update one file, and return the new commit's sha.

    GitHub needs the old file's sha to update it - that is how it refuses to
    overwrite a change somebody else pushed in the meantime.
    """
    _, sha = get_file(repo, path, token)
    body = {
        "message": message,
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
    }
    if sha:
        body["sha"] = sha

    data = call("PUT", f"/repos/{repo}/contents/{path}", token, json=body)
    return data.get("commit", {}).get("sha", "")


def recent_runs(repo: str, token: str, limit: int = 5) -> list[dict]:
    """The latest workflow runs, trimmed to what the page shows."""
    data = call("GET", f"/repos/{repo}/actions/runs?per_page={limit}", token)
    return [
        {
            "name": run.get("name", ""),
            "status": run.get("status", ""),
            "conclusion": run.get("conclusion") or "",
            "started": (run.get("run_started_at") or "")[:16].replace("T", " "),
            "url": run.get("html_url", ""),
        }
        for run in data.get("runs", data.get("workflow_runs", []))
    ]
