"""Set up GitHub Actions from the browser: sign in, push settings, send secrets."""
from __future__ import annotations

import dataclasses

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from agent import paths
from agent.config import load_config, save_config
from agent.github import api, device, repo_secrets
from agent.github.errors import GitHubError
from agent.llm import KEY_NAMES
from agent.secrets_store import get_secret, set_secret
from web.app import templates
from web.steps import progress
from web.workflow import workflow_path

router = APIRouter(prefix="/setup/github")

# Files the app keeps in step with GitHub. state.json is missing on purpose:
# the workflow writes that one, so pushing it from here would undo a real run.
SYNCED = (
    ("data/config.json", "your settings"),
    ("data/topics.json", "your topic list"),
    (".github/workflows/post.yml", "the schedule"),
)

# One pending sign-in at a time - this is a single-user app on your own machine.
_pending: dict[str, str] = {}


def _back(**flash: str) -> RedirectResponse:
    from urllib.parse import urlencode
    query = urlencode({k: v for k, v in flash.items() if v})
    return RedirectResponse(f"/setup/github{'?' + query if query else ''}", status_code=303)


def _token() -> str:
    return get_secret("GITHUB_TOKEN") or ""


def _local_secrets(cfg) -> list[str]:
    """The secrets this machine has that Actions also needs."""
    wanted = [KEY_NAMES.get(cfg.llm_provider), "LINKEDIN_ACCESS_TOKEN"]
    return [name for name in wanted if name and get_secret(name)]


def _repo_file(path: str) -> str:
    """Read one of the synced files from disk."""
    if path.startswith("data/"):
        return (paths.DATA_DIR / path.split("/", 1)[1]).read_text(encoding="utf-8")
    return workflow_path().read_text(encoding="utf-8")


@router.get("", response_class=HTMLResponse)
def page(request: Request, error: str = "", done: str = "") -> HTMLResponse:
    cfg = load_config()
    token = _token()
    login, runs, on_github = "", [], []

    if token:
        try:
            login = api.current_user(token)
            if cfg.github_repo:
                runs = api.recent_runs(cfg.github_repo, token, limit=5)
                on_github = repo_secrets.existing_secrets(cfg.github_repo, token)
        except GitHubError as exc:
            error = error or str(exc)

    return templates.TemplateResponse(
        request=request,
        name="pages/setup_github.html",
        context={
            "cfg": cfg,
            "steps": progress("github"),
            "login": login,
            "connected": bool(login),
            "repo": cfg.github_repo or api.repo_from_remote(),
            "detected": api.repo_from_remote(),
            "synced": SYNCED,
            "needed": _local_secrets(cfg),
            "on_github": on_github,
            "runs": runs,
            "error": error,
            "done": done,
        },
    )


@router.post("/client")
def save_client(client_id: str = Form(""), repo: str = Form("")) -> RedirectResponse:
    cfg = dataclasses.replace(load_config(),
                              github_client_id=client_id.strip(),
                              github_repo=repo.strip())
    save_config(cfg)
    return _back(done="Saved.")


@router.post("/start")
def start() -> JSONResponse:
    """Ask GitHub for the code you type on github.com/login/device."""
    cfg = load_config()
    try:
        flow = device.start(cfg.github_client_id)
    except GitHubError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    _pending["device_code"] = flow["device_code"]
    return JSONResponse({
        "user_code": flow["user_code"],
        "url": flow["verification_uri"],
        "interval": flow["interval"],
    })


@router.post("/poll")
def poll() -> JSONResponse:
    """Called every few seconds by the page until you approve on GitHub."""
    cfg = load_config()
    code = _pending.get("device_code")
    if not code:
        return JSONResponse({"error": "Nothing to wait for. Press Connect again."}, status_code=400)

    try:
        token = device.poll_once(cfg.github_client_id, code)
    except GitHubError as exc:
        _pending.clear()
        return JSONResponse({"error": str(exc)}, status_code=400)

    if token is None:
        return JSONResponse({"status": "waiting"})

    set_secret("GITHUB_TOKEN", token)
    _pending.clear()
    return JSONResponse({"status": "connected", "login": api.current_user(token)})


@router.post("/push")
def push() -> RedirectResponse:
    """Copy the local settings into the repo, one commit per changed file."""
    cfg = load_config()
    token = _token()
    if not (token and cfg.github_repo):
        return _back(error="Connect GitHub and set the repository first.")

    changed: list[str] = []
    try:
        for path, label in SYNCED:
            text = _repo_file(path)
            remote, _ = api.get_file(cfg.github_repo, path, token)
            if remote == text:
                continue
            api.put_file(cfg.github_repo, path, text, f"chore: update {label} from PostCadence", token)
            changed.append(path)
    except (GitHubError, OSError) as exc:
        return _back(error=str(exc))

    return _back(done=f"Pushed {len(changed)} file(s)." if changed else "Everything already matched.")


@router.post("/secrets")
def send_secrets() -> RedirectResponse:
    """Encrypt each local secret and store it on the repository."""
    cfg = load_config()
    token = _token()
    if not (token and cfg.github_repo):
        return _back(error="Connect GitHub and set the repository first.")

    names = _local_secrets(cfg)
    if not names:
        return _back(error="No secrets stored on this machine yet.")

    try:
        key, key_id = repo_secrets.public_key(cfg.github_repo, token)
        for name in names:
            repo_secrets.put_secret(cfg.github_repo, name, get_secret(name), token, key, key_id)
    except GitHubError as exc:
        return _back(error=str(exc))

    return _back(done=f"Sent {len(names)} secret(s): {', '.join(names)}.")


@router.post("/disconnect")
def disconnect() -> RedirectResponse:
    from agent.secrets_store import delete_secret
    delete_secret("GITHUB_TOKEN")
    _pending.clear()
    return _back(done="Disconnected from GitHub on this machine.")
