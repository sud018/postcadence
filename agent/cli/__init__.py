"""Builds the command line from one module per command group."""
from __future__ import annotations

import argparse

from agent.cli import linkedin, model, posting, report, secrets, setup, topics
from agent.cli.ui import console
from agent.config import ConfigError
from agent.linkedin.errors import LinkedInError
from agent.llm.base import LLMError

# Each module owns its own commands and registers them here.
MODULES = (setup, secrets, model, linkedin, topics, posting, report)

# Errors we raise on purpose: show the message, not a traceback.
EXPECTED_ERRORS = (ConfigError, FileNotFoundError, KeyError, ValueError, LLMError, LinkedInError)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m agent", description="PostCadence agent")
    sub = parser.add_subparsers(dest="command", required=True)
    for module in MODULES:
        module.register(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except EXPECTED_ERRORS as exc:
        console.print(f"[red]Error:[/] {exc}")
        return 1
