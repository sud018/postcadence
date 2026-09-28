"""The little badge in the top bar: is GitHub running what you see here?

It asks GitHub, which takes a second, so the page loads first and the badge
fills itself in afterwards (static/js/sync.js). The answer is kept for a minute
so clicking around the app does not call GitHub on every page.
"""
from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse, RedirectResponse

from agent.config import is_first_run, load_or_default
from agent.github import sync
from agent.github.errors import GitHubAuthError, GitHubError
from agent.secrets_store import get_secret

router = APIRouter(prefix="/sync")

CACHE_SECONDS = 60
_cache: dict = {}


def forget_sync_cache() -> None:
    """Call after anything that changes either side, so the badge is honest."""
    _cache.clear()


def _token() -> str:
    try:
        return get_secret("GITHUB_TOKEN") or ""
    except Exception:
        return ""


def _status() -> dict:
    """The badge's whole state, as one small dict."""
    if is_first_run():
        return {"level": "off", "text": "Not set up", "files": [], "behind": 0}

    cfg = load_or_default()
    token = _token()
    if not (cfg.github_repo and token):
        return {"level": "off", "text": "GitHub not connected", "files": [], "behind": 0}

    try:
        files = sync.compare(cfg.github_repo, token)
        behind = sync.newer_runs(cfg.github_repo, token)
    except GitHubAuthError:
        return {"level": "error", "text": "GitHub sign-in expired", "files": [], "behind": 0}
    except (GitHubError, OSError):
        return {"level": "error", "text": "Could not reach GitHub", "files": [], "behind": 0}

    to_push = [f for f in files if f.status != "same"]
    if to_push:
        level, text = "push", f"{len(to_push)} change{'s' if len(to_push) != 1 else ''} not on GitHub"
    elif behind:
        level, text = "pull", f"{behind} new run{'s' if behind != 1 else ''} on GitHub"
    else:
        level, text = "ok", "In sync"

    return {
        "level": level,
        "text": text,
        "files": [{"path": f.path, "label": f.label, "status": f.status} for f in files],
        "behind": behind,
    }


@router.get("/status")
def status(fresh: bool = False) -> JSONResponse:
    now = time.monotonic()
    if fresh or not _cache or now - _cache["at"] > CACHE_SECONDS:
        _cache.update(at=now, value=_status())
    return JSONResponse(_cache["value"])


@router.post("/pull-state")
def pull_state() -> RedirectResponse:
    """Bring the workflow's post history down to this machine."""
    cfg = load_or_default()
    token = _token()
    if not (cfg.github_repo and token):
        return RedirectResponse("/settings?error=Connect+GitHub+first.", status_code=303)

    try:
        count = sync.pull_state(cfg.github_repo, token)
    except GitHubError as exc:
        from urllib.parse import quote
        return RedirectResponse(f"/settings?error={quote(str(exc))}", status_code=303)

    forget_sync_cache()
    return RedirectResponse(f"/settings?done=Pulled+{count}+history+entries+from+GitHub.",
                            status_code=303)
