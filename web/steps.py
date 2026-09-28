"""Which setup steps are finished, worked out from the real config and keyring."""
from __future__ import annotations

from agent.config import load_config
from agent.llm import KEY_NAMES
from agent.schedule import cron_lines
from agent.secrets_store import get_secret
from agent.topics import load_topics
from web.workflow import current_cron, workflow_path

STEPS = [
    ("model", "Model", "/setup"),
    ("linkedin", "LinkedIn", "/setup/linkedin"),
    ("schedule", "Schedule", "/setup/schedule"),
    ("topics", "Topics", "/topics"),
    ("github", "GitHub", "/setup/github"),
]


def completed() -> dict[str, bool]:
    cfg = load_config()
    key_name = KEY_NAMES.get(cfg.llm_provider)
    path = workflow_path()
    in_step = path.exists() and set(current_cron(path.read_text(encoding="utf-8"))) == set(cron_lines(cfg))

    return {
        "model": key_name is None or bool(get_secret(key_name)),
        "linkedin": bool(cfg.linkedin_member_id and get_secret("LINKEDIN_ACCESS_TOKEN")),
        "schedule": in_step,
        "topics": bool(load_topics()),
        "github": bool(cfg.github_repo and get_secret("GITHUB_TOKEN")),
    }


def progress(current: str) -> list[dict]:
    done = completed()
    return [
        {"id": step_id, "label": label, "href": href,
         "done": done[step_id], "current": step_id == current, "number": n}
        for n, (step_id, label, href) in enumerate(STEPS, start=1)
    ]
