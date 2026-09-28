"""Setup step 2: pick a platform, store the LinkedIn app credentials, sign in."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from agent.config import load_or_default, save_config
from agent.linkedin.errors import LinkedInError
from agent.linkedin.oauth import authorize_url, finish, new_state
from agent.secrets_store import get_secret, mask, set_secret
from agent.status import token_days
from web.app import templates
from web.steps import progress

router = APIRouter(prefix="/setup/linkedin")

# One local user, one sign-in at a time: an in-memory set is enough to check `state`.
_pending_states: set[str] = set()

PLATFORMS = [
    {"id": "linkedin", "name": "LinkedIn", "icon": "💼", "ready": True},
    {"id": "x", "name": "X", "icon": "𝕏", "ready": False},
    {"id": "instagram", "name": "Instagram", "icon": "📸", "ready": False},
    {"id": "reddit", "name": "Reddit", "icon": "👽", "ready": False},
]


def callback_url(request: Request) -> str:
    return str(request.url_for("linkedin_callback"))


@router.get("", response_class=HTMLResponse)
def page(request: Request, error: str = "", connected: int = 0) -> HTMLResponse:
    cfg = load_or_default()
    client_id = get_secret("LINKEDIN_CLIENT_ID")
    return templates.TemplateResponse(
        request=request,
        name="pages/setup_linkedin.html",
        context={
            "steps": progress("linkedin"),
            "platforms": PLATFORMS,
            "callback": callback_url(request),
            "client_id": mask(client_id) if client_id else "",
            "has_secret": bool(get_secret("LINKEDIN_CLIENT_SECRET")),
            "member_id": cfg.linkedin_member_id,
            "connected": bool(cfg.linkedin_member_id and get_secret("LINKEDIN_ACCESS_TOKEN")),
            "expires": cfg.linkedin_token_expires,
            "days_left": token_days(cfg),
            "error": error,
            "just_connected": bool(connected),
        },
    )


@router.post("/credentials")
def save_credentials(client_id: str = Form(""), client_secret: str = Form("")) -> RedirectResponse:
    if client_id.strip():
        set_secret("LINKEDIN_CLIENT_ID", client_id.strip())
    if client_secret.strip():
        set_secret("LINKEDIN_CLIENT_SECRET", client_secret.strip())
    return RedirectResponse("/setup/linkedin", status_code=303)


@router.get("/start")
def start(request: Request) -> RedirectResponse:
    client_id = get_secret("LINKEDIN_CLIENT_ID")
    if not client_id or not get_secret("LINKEDIN_CLIENT_SECRET"):
        return _back("Save your LinkedIn app's Client ID and Secret first.")

    state = new_state()
    _pending_states.add(state)
    return RedirectResponse(authorize_url(client_id, callback_url(request), state), status_code=303)


@router.get("/callback", name="linkedin_callback")
def callback(request: Request, code: str = "", state: str = "", error: str = "",
             error_description: str = "") -> RedirectResponse:
    if error:
        return _back(f"LinkedIn said: {error_description or error}")
    if state not in _pending_states:
        return _back("That sign-in link is stale or was not started here. Try Connect again.")
    _pending_states.discard(state)

    try:
        result = finish(code, get_secret("LINKEDIN_CLIENT_ID") or "",
                        get_secret("LINKEDIN_CLIENT_SECRET") or "", callback_url(request))
    except LinkedInError as exc:
        return _back(str(exc))

    set_secret("LINKEDIN_ACCESS_TOKEN", result["access_token"])
    cfg = load_or_default()
    cfg.linkedin_member_id = result["member_id"]
    cfg.linkedin_token_expires = result["expires_on"]
    save_config(cfg)
    return RedirectResponse("/setup/linkedin?connected=1", status_code=303)


def _back(message: str) -> RedirectResponse:
    return RedirectResponse(f"/setup/linkedin?error={quote(message)}", status_code=303)
