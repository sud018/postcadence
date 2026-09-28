"""Setup wizard: pick a provider, prove the key works, choose a model."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from agent.config import PROVIDERS, load_config, save_config
from agent.llm import KEY_NAMES, build
from agent.llm.base import AuthError, LLMError
from agent.llm.catalog import known_models
from agent.secrets_store import get_secret, mask, set_secret
from web.app import templates
from web.steps import progress

router = APIRouter(prefix="/setup")

PROVIDER_CARDS = [
    {"id": "openai", "name": "OpenAI", "note": "GPT-4o and friends", "icon": "🟢",
     "help": "platform.openai.com → API keys"},
    {"id": "anthropic", "name": "Anthropic", "note": "Claude models", "icon": "🟣",
     "help": "console.anthropic.com → API keys"},
    {"id": "gemini", "name": "Gemini", "note": "Google models", "icon": "🔵",
     "help": "aistudio.google.com → Get API key"},
    {"id": "ollama", "name": "Ollama", "note": "Runs on this machine, free", "icon": "⚪",
     "help": "No key needed. Cloud posting will not work with this."},
]


def _state() -> dict:
    """What the wizard already knows, read from the real config and keyring."""
    cfg = load_config()
    key_name = KEY_NAMES.get(cfg.llm_provider)
    key = get_secret(key_name) if key_name else None
    return {
        "cfg": cfg,
        "providers": PROVIDER_CARDS,
        "selected": cfg.llm_provider,
        "key_set": bool(key) or key_name is None,
        "masked": mask(key) if key else "",
        "steps": progress("model"),
    }


@router.get("", response_class=HTMLResponse)
def page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="pages/setup.html", context=_state())


@router.post("/provider", response_class=HTMLResponse)
def save_provider(request: Request, provider: str = Form(...), api_key: str = Form("")) -> HTMLResponse:
    """Validate the key with a real call before storing anything."""
    if provider not in PROVIDERS:
        return _result(request, error=f"Unknown provider {provider!r}.")

    key_name = KEY_NAMES.get(provider)
    api_key = api_key.strip()

    if key_name and not api_key:
        api_key = get_secret(key_name) or ""
        if not api_key:
            return _result(request, error="Paste a key to continue.")

    cfg = load_config()
    cfg.llm_provider = provider
    probe = _probe(provider, api_key, cfg.llm_model)

    if probe["error"]:
        return _result(request, error=probe["error"])

    if key_name and api_key:
        set_secret(key_name, api_key)
    cfg.llm_model = ""              # the old model may not exist on the new provider
    save_config(cfg)

    return _result(request, reply=probe["reply"], models=probe["models"], provider=provider)


def _probe(provider: str, api_key: str, model: str) -> dict:
    """One live call: does the key work, and what models can it use?"""
    try:
        worker = build(provider, api_key, model)   # unsaved key, on purpose
        return {"reply": worker.check(), "models": worker.models(), "error": ""}
    except AuthError as exc:
        return {"reply": "", "models": [], "error": str(exc)}
    except LLMError as exc:
        return {"reply": "", "models": [], "error": str(exc)}


def _result(request: Request, reply: str = "", models: list[str] | None = None,
            provider: str = "", error: str = "") -> HTMLResponse:
    cfg = load_config()
    return templates.TemplateResponse(
        request=request,
        name="partials/provider_result.html",
        context={"reply": reply, "models": models or [], "error": error, "live": True,
                 "provider": provider or cfg.llm_provider, "chosen": cfg.llm_model},
    )


@router.post("/model", response_class=HTMLResponse)
def save_model(request: Request, model: str = Form(...)) -> HTMLResponse:
    cfg = load_config()
    cfg.llm_model = model.strip()
    save_config(cfg)
    return templates.TemplateResponse(
        request=request, name="partials/model_saved.html", context={"model": cfg.llm_model})


@router.get("/models", response_class=HTMLResponse)
def models_for(request: Request, provider: str = "") -> HTMLResponse:
    """The usual models for a provider, offered before any key is checked."""
    cfg = load_config()
    provider = provider or cfg.llm_provider
    return templates.TemplateResponse(
        request=request,
        name="partials/model_choices.html",
        context={"models": known_models(provider), "chosen": cfg.llm_model,
                 "provider": provider, "live": False},
    )
