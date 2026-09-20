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
from agent.linkedin.errors import LinkedInError
from agent.linkedin.oauth import connect
from agent.linkedin.poster import post_text
from agent.topics import TopicError, load_file, load_topics, load_typed,pick_topic,save_topics

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

def cmd_linkedin_connect(args: argparse.Namespace) -> int:
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

def cmd_linkedin_test_post(args: argparse.Namespace) -> int:
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

def cmd_topics_add(args: argparse.Namespace) -> int:
    new = load_file(args.file) if args.file else load_typed(args.text)
    existing = load_topics()
    merged = existing + [t for t in new if t.lower() not in {e.lower() for e in existing}]
    save_topics(merged)
    console.print(f"[green]Added {len(merged) - len(existing)}[/] new topics. Total: {len(merged)}")
    return 0

def cmd_topics_list(args: argparse.Namespace)->int:
    topics = load_topics()
    if not topics:
        console.print("[yellow]No topics yet.[/] Add some with: python -m agent topics add --text \"...\"")
        return 0
    used = load_state().next_topic_index
    table = Table(title=f"Topics ({len(topics)})")
    table.add_column("#", justify="right")
    table.add_column("Topic")
    table.add_column("Status")
    for i,topic in enumerate(topics):
        table.add_row(str(i), topic, "used" if i<used else "queued")
    console.print(table)
    return 0

def cmd_topics_next(args: argparse.Namespace)->int:
    from datetime import date
    cfg = load_config()
    slot = args.slot or cfg.post_times[0]
    pick = pick_topic(load_topics(), load_state(),slot, date.today().isoformat())
    label = "[yellow]repeat[/]" if pick.is_repeat else "[green]new[/]"
    console.print(f"Slot {slot}: {pick.topic}  ({label})")
    return 0

def cmd_topics_clear(args: argparse.Namespace) -> int:
    save_topics([])
    state = load_state()
    state.next_topic_index = 0
    save_state(state)
    console.print("[green]Topics cleared.[/]")
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
    linkedin = sub.add_parser("linkedin", help="LinkedIn connection").add_subparsers(
        dest="action", required=True)
    topics = sub.add_parser("topics", help="manage your topic list").add_subparsers(dest="action", required=True)
    add = topics.add_parser("add")
    add.add_argument("--file", default="")
    add.add_argument("--text", default="")
    add.set_defaults(func=cmd_topics_add)
    topics.add_parser("list").set_defaults(func=cmd_topics_list)
    nxt = topics.add_parser("next")
    nxt.add_argument("--slot", default="")
    nxt.set_defaults(func=cmd_topics_next)
    topics.add_parser("clear").set_defaults(func=cmd_topics_clear)
    linkedin.add_parser("connect").set_defaults(func=cmd_linkedin_connect)
    tp = linkedin.add_parser("test-post")
    tp.add_argument("--text", default="")
    tp.set_defaults(func=cmd_linkedin_test_post)
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
    except (ConfigError, FileNotFoundError, KeyError, ValueError, LLMError, LinkedInError) as exc:
        console.print(f"[red]Error:[/] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
