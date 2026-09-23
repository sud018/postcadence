"""status, cron and token-check: read-only views of the agent."""
from __future__ import annotations

import argparse
import os
from datetime import date

from agent.cli.ui import Table, console
from agent.config import load_config
from agent.schedule import cron_lines, local_now
from agent.state import load_state
from agent.status import counts, next_run, post_link, recent, token_days, until
from agent.topics import load_topics

STATUS_COLOURS = {"posted": "green", "failed": "red", "skipped": "yellow"}


def cmd_status(args: argparse.Namespace) -> int:
    cfg = load_config()
    state = load_state()
    topics = load_topics()
    now = local_now(cfg)

    slot, when = next_run(cfg, now)
    remaining = max(0, len(topics) - state.next_topic_index)
    days = token_days(cfg)
    tally = counts(state)

    summary = Table(show_header=False, title="PostCadence")
    summary.add_column("", style="dim")
    summary.add_column("")
    summary.add_row("Now", now.strftime("%Y-%m-%d %H:%M %Z"))
    summary.add_row("Mode", cfg.mode)
    summary.add_row("Next run", f"{slot} on {when.date()} ({until(when, now)})")
    summary.add_row("Topics", f"{remaining} queued of {len(topics)}")
    summary.add_row("Token", "unknown" if days is None else f"{days} days left")
    summary.add_row("History", ", ".join(f"{k}: {v}" for k, v in tally.items()) or "nothing yet")
    console.print(summary)

    entries = recent(state)
    if not entries:
        return 0

    table = Table(title="Recent posts")
    for column in ("Date", "Slot", "Topic", "Status", "Link"):
        table.add_column(column)
    for entry in entries:
        colour = STATUS_COLOURS.get(entry.status, "white")
        table.add_row(entry.date, entry.slot, entry.topic[:40],
                      f"[{colour}]{entry.status}[/]", post_link(entry) or entry.error[:30])
    console.print(table)
    return 0


def cmd_cron(args: argparse.Namespace) -> int:
    cfg = load_config()
    console.print(f"For {cfg.post_times} in {cfg.timezone} (mode: {cfg.mode}), put these in post.yml:\n")
    for line in cron_lines(cfg):
        console.print(f'    - cron: "{line}"')
    return 0


def cmd_token_check(args: argparse.Namespace) -> int:
    """Report days left on the LinkedIn token, and tell Actions via GITHUB_OUTPUT."""
    cfg = load_config()
    if not cfg.linkedin_token_expires:
        console.print("[yellow]No expiry recorded.[/] Run: python -m agent linkedin connect")
        return 0

    days_left = (date.fromisoformat(cfg.linkedin_token_expires) - date.today()).days
    expiring = days_left <= args.days
    colour = "red" if expiring else "green"
    console.print(f"LinkedIn token expires {cfg.linkedin_token_expires} - [{colour}]{days_left} days left[/]")

    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"days_left={days_left}\n")
            handle.write(f"expiring={'true' if expiring else 'false'}\n")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    sub.add_parser("status", help="next run, topics left, recent posts").set_defaults(func=cmd_status)
    sub.add_parser("cron", help="print the cron lines for your schedule").set_defaults(func=cmd_cron)

    token = sub.add_parser("token-check", help="days left on the LinkedIn token")
    token.add_argument("--days", type=int, default=14)
    token.set_defaults(func=cmd_token_check)
