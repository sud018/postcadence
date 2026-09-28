"""The page you land on."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from agent.config import ConfigError
from web import health
from web.app import templates
from web.deps import link_for, snapshot

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    try:
        data = snapshot()
    except (FileNotFoundError, ConfigError) as exc:
        return templates.TemplateResponse(
            request=request, name="pages/needs_setup.html", context={"error": str(exc)})

    return templates.TemplateResponse(
        request=request,
        name="pages/dashboard.html",
        context={
            "d": data,
            "link_for": link_for,
            # the dashboard only shouts about things that break posting
            "issues": [i for i in health.issues(data.cfg) if i.level != "info"],
        },
    )
