"""secret set / delete / push: credentials, never printed in full."""
from __future__ import annotations

import argparse
import shutil
import subprocess
from getpass import getpass

from agent.cli.ui import console
from agent.secrets_store import KNOWN_SECRETS, delete_secret, get_secret, mask, set_secret

# Only these are needed by GitHub Actions; the client id and secret stay local.
PUSHABLE = ("OPENAI_API_KEY", "LINKEDIN_ACCESS_TOKEN")


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


def cmd_secret_push(args: argparse.Namespace) -> int:
    gh = shutil.which("gh")
    if not gh:
        console.print("[red]gh not found on PATH.[/] Open a new terminal, or install: winget install GitHub.cli")
        return 1

    for name in PUSHABLE:
        value = get_secret(name)
        if not value:
            console.print(f"[yellow]Skipping {name}[/] - not set locally")
            continue
        subprocess.run([gh, "secret", "set", name], input=value, text=True, check=True)
        console.print(f"[green]Pushed[/] {name} to GitHub")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    secret = sub.add_parser("secret", help="manage secrets").add_subparsers(dest="action", required=True)

    setter = secret.add_parser("set", help="store a credential in the OS keyring")
    setter.add_argument("name", choices=sorted(KNOWN_SECRETS))
    setter.set_defaults(func=cmd_secret_set)

    deleter = secret.add_parser("delete", help="remove a stored credential")
    deleter.add_argument("name", choices=sorted(KNOWN_SECRETS))
    deleter.set_defaults(func=cmd_secret_delete)

    secret.add_parser("push", help="upload keys to GitHub Actions secrets").set_defaults(func=cmd_secret_push)
