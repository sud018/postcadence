"""topics add / list / next / clear: the queue the agent writes from."""
from __future__ import annotations

import argparse
from datetime import date

from agent.cli.ui import Table, console
from agent.config import load_config
from agent.state import load_state, save_state
from agent.topics import load_file, load_topics, load_typed, pick_topic, save_topics


def cmd_add(args: argparse.Namespace) -> int:
    new = load_file(args.file) if args.file else load_typed(args.text)
    existing = load_topics()
    merged = existing + [t for t in new if t.lower() not in {e.lower() for e in existing}]
    save_topics(merged)
    console.print(f"[green]Added {len(merged) - len(existing)}[/] new topics. Total: {len(merged)}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    topics = load_topics()
    if not topics:
        console.print('[yellow]No topics yet.[/] Add some with: python -m agent topics add --text "..."')
        return 0

    used = load_state().next_topic_index
    table = Table(title=f"Topics ({len(topics)})")
    table.add_column("#", justify="right")
    table.add_column("Topic")
    table.add_column("Status")
    for index, topic in enumerate(topics):
        table.add_row(str(index), topic, "used" if index < used else "queued")
    console.print(table)
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    cfg = load_config()
    slot = args.slot or cfg.post_times[0]
    pick = pick_topic(load_topics(), load_state(), slot, date.today().isoformat())
    label = "[yellow]repeat[/]" if pick.is_repeat else "[green]new[/]"
    console.print(f"Slot {slot}: {pick.topic}  ({label})")
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    save_topics([])
    state = load_state()
    state.next_topic_index = 0          # the bookmark must reset with the list
    save_state(state)
    console.print("[green]Topics cleared.[/]")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    topics = sub.add_parser("topics", help="manage your topic list").add_subparsers(
        dest="action", required=True)

    add = topics.add_parser("add", help="add topics from a file or typed text")
    add.add_argument("--file", default="", help="xlsx, docx, pdf, csv, txt or md")
    add.add_argument("--text", default="", help='topics separated by ";" or newlines')
    add.set_defaults(func=cmd_add)

    topics.add_parser("list", help="show every topic and whether it is used").set_defaults(func=cmd_list)

    nxt = topics.add_parser("next", help="show what would be picked, changing nothing")
    nxt.add_argument("--slot", default="")
    nxt.set_defaults(func=cmd_next)

    topics.add_parser("clear", help="remove all topics and reset the bookmark").set_defaults(func=cmd_clear)
