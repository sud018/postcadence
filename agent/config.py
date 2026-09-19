"""User settings chosen in the setup wizard. Contains NO secrets."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from agent import paths
from agent.jsonio import read_json, write_json

PROVIDERS = ("openai", "anthropic", "gemini", "ollama")
MODES = ("auto", "preview")
TONES = ("professional", "causual", "storytelling")
TIMEOUT_ACTIONS = ("post", "skip")
MAX_POSTS_PER_DAY = 5
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ConfigError(ValueError):
    """Raised when settings are invalid."""


@dataclass
class Config:
    llm_provider: str = "openai"
    llm_model: str = ""
    timezone: str = "America/Los_Angeles"
    posts_per_day: int = 1
    post_times: list[str] = field(default_factory=lambda: ["09:00"])
    mode: str = "auto"
    tone: str = "professional"
    preview_minutes: int = 30
    preview_timeout_action: str = "post"
    linkedin_member_id: str = ""
    linkedin_token_expires: str = "" 

    def validate(self) -> None:
        errors: list[str] = []

        if self.llm_provider not in PROVIDERS:
            errors.append(f"llm_provider must be one of {PROVIDERS}")

        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            errors.append(f"unknown timezone: {self.timezone!r}")

        if not 1 <= self.posts_per_day <= MAX_POSTS_PER_DAY:
            errors.append(f"posts_per_day must be 1-{MAX_POSTS_PER_DAY}")

        bad = [t for t in self.post_times if not _TIME_RE.match(t)]
        if bad:
            errors.append(f"post_times must be HH:MM (24h), got {bad}")
        if len(self.post_times) != self.posts_per_day:
            errors.append("number of post_times must equal posts_per_day")
        if len(set(self.post_times)) != len(self.post_times):
            errors.append("post_times must not repeat")

        if self.mode not in MODES:
            errors.append(f"mode must be one of {MODES}")
        if not 5 <= self.preview_minutes <= 240:
            errors.append("preview_minutes must be 5-240")
        if self.preview_timeout_action not in TIMEOUT_ACTIONS:
            errors.append(f"preview_timeout_action must be one of {TIMEOUT_ACTIONS}")
        if self.tone not in TONES:
            errors.append(f"tone must be one of {TONES}")
        if errors:
            raise ConfigError("Invalid config:\n  - " + "\n  - ".join(errors))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Config:
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        cfg = cls(**known)
        cfg.post_times = sorted(cfg.post_times)
        return cfg


def load_config(path: Path = paths.CONFIG_FILE) -> Config:
    if not path.exists():
        raise FileNotFoundError(f"No config at {path}. Run: python -m agent init")
    cfg = Config.from_dict(read_json(path))
    cfg.validate()
    return cfg


def save_config(cfg: Config, path: Path = paths.CONFIG_FILE) -> None:
    cfg.post_times = sorted(cfg.post_times)
    cfg.validate()
    write_json(path, cfg.to_dict())
