"""check-llm: prove the configured provider and key work."""
from __future__ import annotations

import argparse

from agent.cli.ui import console
from agent.config import load_config
from agent.llm import get_provider


def cmd_check_llm(args: argparse.Namespace) -> int:
    cfg = load_config()
    provider = get_provider(cfg)
    console.print(f"Provider: [cyan]{provider.name}[/] · model: [cyan]{provider.model}[/]")
    console.print(f"Model replied: [green]{provider.check()}[/]")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    sub.add_parser("check-llm", help="verify the API key works").set_defaults(func=cmd_check_llm)
