"""init and show: create the data files, then inspect them."""
from __future__ import annotations

import argparse

from agent import paths
from agent.cli.ui import Table, console
from agent.config import Config, save_config
from agent.secrets_store import KNOWN_SECRETS, get_secret, mask
from agent.state import load_state, save_state


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
    from agent.config import load_config

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


def register(sub: argparse._SubParsersAction) -> None:
    init = sub.add_parser("init", help="create default config and state files")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    sub.add_parser("show", help="show config, state and masked secrets").set_defaults(func=cmd_show)
