"""The topics screen: list, add, import, reorder, rename, delete."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from agent.state import load_state, save_state
from agent.topics import load_file, load_topics, load_typed, save_topics
from agent.topics.edit import merge, move, remove_at, rename_at
from agent.topics.loader import TopicError
from web.app import templates

router = APIRouter(prefix="/topics")


def _view(request: Request, message: str = "", error: str = "") -> HTMLResponse:
    """Render the table on its own - every action returns this."""
    topics = load_topics()
    bookmark = load_state().next_topic_index
    return templates.TemplateResponse(
        request=request,
        name="partials/topic_table.html",
        context={
            "topics": topics,
            "bookmark": bookmark,
            "queued": max(0, len(topics) - bookmark),
            "message": message,
            "error": error,
        },
    )


def _persist(topics: list[str], bookmark: int | None = None) -> None:
    save_topics(topics)
    if bookmark is not None:
        state = load_state()
        state.next_topic_index = bookmark
        save_state(state)


@router.get("", response_class=HTMLResponse)
def page(request: Request) -> HTMLResponse:
    topics = load_topics()
    bookmark = load_state().next_topic_index
    return templates.TemplateResponse(
        request=request,
        name="pages/topics.html",
        context={"topics": topics, "bookmark": bookmark,
                 "queued": max(0, len(topics) - bookmark)},
    )


@router.post("/add", response_class=HTMLResponse)
def add(request: Request, text: str = Form("")) -> HTMLResponse:
    try:
        incoming = load_typed(text)
    except TopicError as exc:
        return _view(request, error=str(exc))

    before = load_topics()
    after = merge(before, incoming)
    _persist(after)
    added = len(after) - len(before)
    return _view(request, message=f"Added {added} topic{'s' if added != 1 else ''}.")


@router.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    suffix = Path(file.filename or "").suffix or ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(await file.read())
        temp_path = handle.name

    try:
        incoming = load_file(temp_path)
    except TopicError as exc:
        return _view(request, error=str(exc))
    finally:
        Path(temp_path).unlink(missing_ok=True)

    before = load_topics()
    after = merge(before, incoming)
    _persist(after)
    added = len(after) - len(before)
    return _view(request, message=f"Imported {added} new topic{'s' if added != 1 else ''} "
                                  f"from {file.filename}.")


@router.post("/delete", response_class=HTMLResponse)
def delete(request: Request, index: int = Form(...)) -> HTMLResponse:
    try:
        topics, bookmark = remove_at(load_topics(), index, load_state().next_topic_index)
    except TopicError as exc:
        return _view(request, error=str(exc))
    _persist(topics, bookmark)
    return _view(request, message="Topic removed.")


@router.post("/move", response_class=HTMLResponse)
def reorder(request: Request, index: int = Form(...), delta: int = Form(...)) -> HTMLResponse:
    try:
        topics, bookmark = move(load_topics(), index, delta, load_state().next_topic_index)
    except TopicError as exc:
        return _view(request, error=str(exc))
    _persist(topics, bookmark)
    return _view(request)


@router.post("/rename", response_class=HTMLResponse)
def rename(request: Request, index: int = Form(...), text: str = Form(...)) -> HTMLResponse:
    try:
        topics = rename_at(load_topics(), index, text)
    except TopicError as exc:
        return _view(request, error=str(exc))
    _persist(topics)
    return _view(request, message="Topic updated.")


@router.post("/bookmark", response_class=HTMLResponse)
def set_bookmark(request: Request, value: int = Form(...)) -> HTMLResponse:
    topics = load_topics()
    _persist(topics, max(0, min(value, len(topics))))
    return _view(request, message="Queue position updated.")
