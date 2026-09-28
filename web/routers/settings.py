"""One page for everything after setup: voice, connections, health, sync."""
from __future__ import annotations

import dataclasses
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from agent.config import TONES, ConfigError, is_first_run, load_or_default, save_config
from agent.llm import KEY_NAMES
from agent.secrets_store import get_secret
from agent.status import token_days
from web import health
from web.app import templates

router = APIRouter(prefix="/settings")

MAX_CONTEXT = 600   # enough for a short bio; longer just dilutes the prompt


def _has(name: str | None) -> bool:
    try:
        return bool(name and get_secret(name))
    except Exception:
        return False


@router.get("", response_class=HTMLResponse)
def page(request: Request, error: str = "", done: str = "") -> HTMLResponse:
    cfg = load_or_default()
    key = KEY_NAMES.get(cfg.llm_provider)

    connections = [
        {
            "name": "Writer",
            "icon": "✍️",
            "value": f"{cfg.llm_provider} · {cfg.llm_model or 'default model'}",
            "ok": key is None or _has(key),
            "note": "key stored" if key is None or _has(key) else f"{key} missing",
            "href": "/setup", "action": "Change",
        },
        {
            "name": "LinkedIn",
            "icon": "💼",
            "value": cfg.linkedin_member_id or "not connected",
            "ok": bool(cfg.linkedin_member_id and _has("LINKEDIN_ACCESS_TOKEN")),
            "note": _token_note(token_days(cfg)),
            "href": "/setup/linkedin", "action": "Reconnect",
        },
        {
            "name": "GitHub",
            "icon": "🤖",
            "value": cfg.github_repo or "no repository",
            "ok": bool(cfg.github_repo and _has("GITHUB_TOKEN")),
            "note": "signed in" if _has("GITHUB_TOKEN") else "not signed in",
            "href": "/setup/github", "action": "Manage",
        },
    ]

    return templates.TemplateResponse(
        request=request,
        name="pages/settings.html",
        context={
            "cfg": cfg,
            "tones": TONES,
            "max_context": MAX_CONTEXT,
            "connections": connections,
            "issues": health.issues(cfg),
            "first_run": is_first_run(),
            "error": error,
            "done": done,
        },
    )


def _token_note(days: int | None) -> str:
    if days is None:
        return "no token"
    if days < 0:
        return "token expired"
    return f"token valid {days} more day{'s' if days != 1 else ''}"


@router.post("/voice")
def save_voice(tone: str = Form(...), author_context: str = Form("")) -> RedirectResponse:
    """How the writer sounds, and what it may say about you."""
    context = author_context.strip()
    if len(context) > MAX_CONTEXT:
        return _back(error=f"Keep the note under {MAX_CONTEXT} characters (it is {len(context)}).")

    try:
        save_config(dataclasses.replace(load_or_default(), tone=tone, author_context=context))
    except ConfigError as exc:
        return _back(error=str(exc))

    return _back(done="Voice saved. Push to GitHub so the scheduled posts use it too.")


def _back(**flash: str) -> RedirectResponse:
    query = urlencode({k: v for k, v in flash.items() if v})
    return RedirectResponse(f"/settings{'?' + query if query else ''}", status_code=303)
