"""Setup step 3: how often and when to post - and keep post.yml in step."""
from __future__ import annotations

from dataclasses import replace
from zoneinfo import available_timezones

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from agent.config import MAX_POSTS_PER_DAY, ConfigError, load_or_default, save_config
from agent.schedule import cron_lines
from web.app import templates
from web.steps import progress
from web.workflow import WorkflowError, apply

router = APIRouter(prefix="/setup/schedule")

COMMON_ZONES = [
    "America/Los_Angeles", "America/Denver", "America/Chicago", "America/New_York",
    "Europe/London", "Europe/Berlin", "Asia/Kolkata", "Asia/Singapore", "Australia/Sydney",
]


def _zones() -> list[str]:
    rest = sorted(z for z in available_timezones() if "/" in z and z not in COMMON_ZONES)
    return COMMON_ZONES + rest


def _render(request: Request, cfg, errors: list[str] | None = None,
            saved: bool = False, changed: bool = False) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="pages/setup_schedule.html",
        context={
            "steps": progress("schedule"),
            "cfg": cfg,
            "zones": _zones(),
            "max_posts": MAX_POSTS_PER_DAY,
            "cron": cron_lines(cfg) if not errors else [],
            "errors": errors or [],
            "saved": saved,
            "changed": changed,
        },
    )


@router.get("", response_class=HTMLResponse)
def page(request: Request) -> HTMLResponse:
    return _render(request, load_or_default())


@router.post("", response_class=HTMLResponse)
def save(
    request: Request,
    post_times: list[str] = Form(...),
    timezone: str = Form(...),
    mode: str = Form("auto"),
    preview_minutes: int = Form(30),
    preview_timeout_action: str = Form("post"),
    catch_up_hours: int = Form(6),
) -> HTMLResponse:
    times = sorted({t.strip() for t in post_times if t.strip()})
    candidate = replace(
        load_or_default(),
        posts_per_day=len(times),
        post_times=times,
        timezone=timezone.strip(),
        mode=mode,
        preview_minutes=preview_minutes,
        preview_timeout_action=preview_timeout_action,
        catch_up_hours=catch_up_hours,
    )

    try:
        save_config(candidate)                       # validates before writing
    except ConfigError as exc:
        lines = [line.strip(" -") for line in str(exc).splitlines()[1:]]
        return _render(request, candidate, errors=lines)

    try:
        _, changed = apply(candidate)                # keep post.yml in step
    except WorkflowError as exc:
        return _render(request, candidate, errors=[str(exc)])

    return _render(request, candidate, saved=True, changed=changed)
