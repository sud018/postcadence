"""Punctuality: let an outside clock start the workflow when GitHub's is late.

Everything on this page is read-only except the test button. The page exists
because the alternative is a README the user has to translate into a web form
by hand, and every hand translation is a chance to paste the wrong thing.
"""
from __future__ import annotations

import json
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from agent.config import load_or_default
from agent.github import dispatch
from agent.github.errors import GitHubError
from agent.schedule import trigger_times
from agent.secrets_store import get_secret
from web.app import templates

router = APIRouter(prefix="/setup/trigger")

TOKEN_SCOPE = "Actions: Read and write"


def _token() -> str:
    try:
        return get_secret("GITHUB_TOKEN") or ""
    except Exception:              # a locked or missing keyring is just "no token"
        return ""


def _back(**flash: str) -> RedirectResponse:
    query = urlencode({k: v for k, v in flash.items() if v})
    return RedirectResponse(f"/setup/trigger{'?' + query if query else ''}", status_code=303)


@router.get("", response_class=HTMLResponse)
def page(request: Request, error: str = "", done: str = "") -> HTMLResponse:
    cfg = load_or_default()
    repo = cfg.github_repo

    return templates.TemplateResponse(request, "pages/setup_trigger.html", {
        "cfg": cfg,
        "repo": repo,
        "connected": bool(repo and _token()),
        "url": dispatch.url(repo or "YOUR-NAME/YOUR-REPO"),
        "headers": dispatch.HEADERS,
        # Pretty-printed so it can be pasted into a form field and still read.
        "body": json.dumps(dispatch.body(), indent=2),
        "times": trigger_times(cfg),
        "token_scope": TOKEN_SCOPE,
        "error": error,
        "done": done,
    })


@router.post("/test")
def test() -> RedirectResponse:
    """Fire one dry run, so a mistake is found now rather than at 09:00.

    Dry run means the model still writes a post and the run still shows up in
    the Actions tab, but nothing reaches LinkedIn. That is exactly the proof
    wanted here: the trigger works, and it cost nothing.
    """
    cfg = load_or_default()
    token = _token()
    if not (cfg.github_repo and token):
        return _back(error="Connect GitHub first - this page needs the repo and a token.")

    try:
        dispatch.run_now(cfg.github_repo, token, dry_run=True)
    except GitHubError as exc:
        return _back(error=str(exc))

    return _back(done="Sent. It should appear in the Actions tab within a few seconds.")
