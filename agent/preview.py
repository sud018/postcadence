"""Draft previews as GitHub Issues, so you can approve from your phone."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

API = "https://api.github.com"
START = "<!-- post:start -->"
END = "<!-- post:end -->"
BODY = re.compile(re.escape(START) + r"(.*?)" + re.escape(END), re.DOTALL)
APPROVE = re.compile(r"^\s*/approve\b", re.MULTILINE)
CANCEL = re.compile(r"^\s*/cancel\b", re.MULTILINE)
LABEL = "postcadence-draft"


class PreviewError(RuntimeError):
    """Something went wrong talking to the GitHub API."""


@dataclass
class Draft:
    number: int
    text: str
    decision: str          # approve / cancel / none
    created_at: str = ""   # when the issue was opened, from GitHub (UTC)

    def minutes_open(self, now: datetime | None = None) -> float:
        """How long you have had to look at it.

        The review window is measured from this, not from the clock, because
        GitHub can start a scheduled run an hour or more late.
        """
        if not self.created_at:
            return 0.0
        opened = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        now = now or datetime.now(timezone.utc)
        return (now - opened).total_seconds() / 60


def _env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise PreviewError(f"{name} is not set. Preview mode only works inside GitHub Actions.")
    return value


def _call(method: str, path: str, token: str, **kwargs) -> dict | list:
    response = requests.request(
        method,
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30,
        **kwargs,
    )
    if response.status_code >= 300:
        raise PreviewError(f"GitHub API {method} {path} failed ({response.status_code}): {response.text[:300]}")
    return response.json()


def title_for(date: str, slot: str) -> str:
    return f"Draft post for {date} {slot}"


def build_body(topic: str, text: str, slot: str, timeout_action: str, minutes: int) -> str:
    fallback = "publish it anyway" if timeout_action == "post" else "skip this slot"
    return (
        f"**Topic:** {topic}\n\n"
        f"Comment `/approve` to publish, or `/cancel` to skip.\n"
        f"You can also edit the text below and it will publish as edited.\n"
        f"If nothing happens within about {minutes} minutes, the agent will {fallback} at {slot}.\n\n"
        f"---\n\n{START}\n{text}\n{END}\n"
    )


def extract_text(body: str) -> str:
    """Pull the post out of an issue body, so edits between the markers count."""
    match = BODY.search(body or "")
    if not match:
        raise PreviewError("Could not find the post markers in the issue body.")
    return match.group(1).strip()


def decide(comments: list[dict]) -> str:
    """Newest instruction wins, so a /cancel after an /approve is respected."""
    for comment in reversed(comments):
        text = comment.get("body", "")
        if CANCEL.search(text):
            return "cancel"
        if APPROVE.search(text):
            return "approve"
    return "none"


def open_draft(date: str, slot: str, token: str = "", repo: str = "") -> Draft | None:
    """Find today's open draft for this slot, with its current text and decision."""
    token = token or _env("GITHUB_TOKEN")
    repo = repo or _env("GITHUB_REPOSITORY")

    issues = _call("GET", f"/repos/{repo}/issues?state=open&labels={LABEL}&per_page=50", token)
    wanted = title_for(date, slot)
    match = next((issue for issue in issues if issue.get("title") == wanted), None)
    if match is None:
        return None

    comments = _call("GET", f"/repos/{repo}/issues/{match['number']}/comments?per_page=100", token)
    return Draft(number=match["number"], text=extract_text(match.get("body", "")),
                 decision=decide(comments), created_at=match.get("created_at", ""))


def create_draft(date: str, slot: str, topic: str, text: str, timeout_action: str,
                 minutes: int, token: str = "", repo: str = "") -> int:
    token = token or _env("GITHUB_TOKEN")
    repo = repo or _env("GITHUB_REPOSITORY")

    issue = _call("POST", f"/repos/{repo}/issues", token, json={
        "title": title_for(date, slot),
        "body": build_body(topic, text, slot, timeout_action, minutes),
        "labels": [LABEL],
    })
    return issue["number"]


def close_draft(number: int, comment: str, token: str = "", repo: str = "") -> None:
    token = token or _env("GITHUB_TOKEN")
    repo = repo or _env("GITHUB_REPOSITORY")
    _call("POST", f"/repos/{repo}/issues/{number}/comments", token, json={"body": comment})
    _call("PATCH", f"/repos/{repo}/issues/{number}", token, json={"state": "closed"})
