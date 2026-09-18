"""Command-line entry point:  python -m agent <command>"""
from __future__ import annotations

import argparse
import sys
from getpass import getpass

from rich.console import Console
from rich.table import Table

from agent import paths
from agent.config import Config, ConfigError, load_config, save_config
from agent.secrets_store import KNOWN_SECRETS, delete_secret, get_secret, mask, set_secret
from agent.state import load_state, save_state
from agent.llm import get_provider
from agent.llm.base import LLMError

console = Console()


def cmd_init(args: argparse.Namespace) -> int:
    if paths.CONFIG_FILE.exists() and not args.force:
        console.print("[yellow]Config already exists.[/] Use --force to overwrite.")
        return 1
    save_config(Config())
    save_state(load_state())
    console.print(f"[green]Created[/] {paths.CONFIG_FILE.relative_to(paths.ROOT)}")
    console.print(f"[green]Created[/] {paths.STATE_FILE.relative_to(paths.ROOT)}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    cfg = load_config()
    table = Table(title="PostCadence config")
    table.add_column("Setting")
    table.add_column("Value")
    for key, value in cfg.to_dict().items():
        table.add_row(key, str(value))
    console.print(table)

    state = load_state()
    console.print(f"Next topic index: {state.next_topic_index} · History entries: {len(state.history)}")

    secrets = Table(title="Secrets (masked)")
    secrets.add_column("Name")
    secrets.add_column("Value")
    for name in sorted(KNOWN_SECRETS):
        secrets.add_row(name, mask(get_secret(name)))
    console.print(secrets)
    return 0


def cmd_secret_set(args: argparse.Namespace) -> int:
    value = getpass(f"Paste {args.name} (input hidden): ")
    set_secret(args.name, value)
    console.print(f"[green]Saved[/] {args.name} = {mask(value)}")
    return 0


def cmd_secret_delete(args: argparse.Namespace) -> int:
    if delete_secret(args.name):
        console.print(f"[green]Deleted[/] {args.name}")
    else:
        console.print(f"[yellow]{args.name} was not set[/]")
    return 0

def cmd_check_llm(args: argparse.Namespace) -> int:
    cfg = load_config()
    provider = get_provider(cfg)
    console.print(f"Provider: [cyan]{provider.name}[/] · model: [cyan]{provider.model}[/]")
    console.print(f"Model replied: [green]{provider.check()}[/]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m agent", description="PostCadence agent")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create default config and state files")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    sub.add_parser("show", help="show config, state and masked secrets").set_defaults(func=cmd_show)
    sub.add_parser("check-llm", help="verify the API key works").set_defaults(func=cmd_check_llm)
    secret = sub.add_parser("secret", help="manage secrets").add_subparsers(dest="action", required=True)
    s = secret.add_parser("set")
    s.add_argument("name", choices=sorted(KNOWN_SECRETS))
    s.set_defaults(func=cmd_secret_set)
    d = secret.add_parser("delete")
    d.add_argument("name", choices=sorted(KNOWN_SECRETS))
    d.set_defaults(func=cmd_secret_delete)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, FileNotFoundError, KeyError, ValueError, LLMError) as exc:
        console.print(f"[red]Error:[/] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
