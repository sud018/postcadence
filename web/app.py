"""FastAPI application factory."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agent import __version__

WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


def create_app() -> FastAPI:
    app = FastAPI(title="PostCadence", version=__version__, docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

    from web.routers import dashboard, drafts, linkedin, schedule, topics, wizard

    app.include_router(dashboard.router)
    app.include_router(topics.router)
    app.include_router(wizard.router)
    app.include_router(drafts.router)
    app.include_router(linkedin.router)
    app.include_router(schedule.router)
    return app


app = create_app()
