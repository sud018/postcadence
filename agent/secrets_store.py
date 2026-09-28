"""Read and write secrets without ever putting them in files.

Lookup order for get_secret("OPENAI_API_KEY"):
  1. Environment variable OPENAI_API_KEY  -> how GitHub Actions passes secrets
  2. OS keyring (Windows Credential Manager) -> how your PC stores them
"""
from __future__ import annotations

import os

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

SERVICE = "postcadence"

# Every secret the app is allowed to use. Typos fail loudly instead of silently.
KNOWN_SECRETS = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "LINKEDIN_CLIENT_ID",
    "LINKEDIN_CLIENT_SECRET",
    "LINKEDIN_ACCESS_TOKEN",
    "GITHUB_TOKEN",
}


def _check(name: str) -> None:
    if name not in KNOWN_SECRETS:
        raise KeyError(f"Unknown secret {name!r}. Known: {sorted(KNOWN_SECRETS)}")


def get_secret(name: str) -> str | None:
    _check(name)
    value = os.environ.get(name)
    if value:
        return value
    try:
        return keyring.get_password(SERVICE, name)
    except KeyringError:
        return None


def set_secret(name: str, value: str) -> None:
    _check(name)
    value = value.strip()
    if not value:
        raise ValueError("Secret value is empty")
    keyring.set_password(SERVICE, name, value)


def delete_secret(name: str) -> bool:
    _check(name)
    try:
        keyring.delete_password(SERVICE, name)
        return True
    except PasswordDeleteError:
        return False


def mask(value: str | None) -> str:
    """'sk-abc123xyz789' -> 'sk-a…z789'. Safe to print."""
    if not value:
        return "(not set)"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}…{value[-4:]}"
