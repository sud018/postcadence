"""linkedin connect / test-post: sign in once, and send a one-off post."""
from __future__ import annotations

import argparse

from agent.cli.ui import console
from agent.config import load_config, save_config
from agent.linkedin.oauth import connect
from agent.linkedin.poster import post_text
from agent.secrets_store import get_secret, set_secret


def cmd_connect(args: argparse.Namespace) -> int:
    client_id = get_secret("LINKEDIN_CLIENT_ID")
    client_secret = get_secret("LINKEDIN_CLIENT_SECRET")
    if not client_id or not client_secret:
        console.print("[red]Store your app credentials first:[/] python -m agent secret set LINKEDIN_CLIENT_ID")
        return 1

    result = connect(client_id, client_secret)
    set_secret("LINKEDIN_ACCESS_TOKEN", result["access_token"])

    cfg = load_config()
    cfg.linkedin_member_id = result["member_id"]
    cfg.linkedin_token_expires = result["expires_on"]
    save_config(cfg)

    console.print(f"[green]Connected.[/] Member id: {result['member_id']}")
    console.print(f"Token valid until [cyan]{result['expires_on']}[/]")
    return 0


def cmd_test_post(args: argparse.Namespace) -> int:
    cfg = load_config()
    token = get_secret("LINKEDIN_ACCESS_TOKEN")
    if not token or not cfg.linkedin_member_id:
        console.print("[red]Not connected.[/] Run: python -m agent linkedin connect")
        return 1

    text = args.text or "Testing my posting agent. This post was published from Python."
    console.print(f"About to post:\n\n{text}\n")
    if input("Publish this to your LinkedIn profile? [y/N] ").strip().lower() != "y":
        console.print("Cancelled.")
        return 0

    urn = post_text(text, token, cfg.linkedin_member_id)
    console.print(f"[green]Posted.[/] {urn}")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    linkedin = sub.add_parser("linkedin", help="LinkedIn connection").add_subparsers(
        dest="action", required=True)

    linkedin.add_parser("connect", help="sign in and store an access token").set_defaults(func=cmd_connect)

    test_post = linkedin.add_parser("test-post", help="publish one post by hand")
    test_post.add_argument("--text", default="")
    test_post.set_defaults(func=cmd_test_post)
