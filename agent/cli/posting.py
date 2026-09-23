"""run and run-due: the commands that actually publish."""
from __future__ import annotations

import argparse

from agent.cli.ui import console
from agent.config import load_config
from agent.run import RunResult, decide_preview, prepare_preview, run_once
from agent.schedule import due_slots, prepare_slots
from agent.state import load_state


def _show(result: RunResult, heading: str = "") -> None:
    if heading:
        console.print(f"\n[cyan]{heading}[/] {result.status}")
    if result.topic:
        console.print(f"[cyan]Topic:[/] {result.topic}\n")
    if result.text:
        console.print(result.text)
        console.print(f"\n[dim]{len(result.text)} characters[/]")
    if result.post_id:
        console.print(f"[green]Posted.[/] {result.post_id}")
    if result.status == "dry-run":
        console.print("[yellow]Dry run - nothing was published.[/]")
    if result.reason:
        console.print(f"[dim]{result.reason}[/]")


def cmd_run(args: argparse.Namespace) -> int:
    cfg = load_config()
    slot = args.slot or cfg.post_times[0]
    _show(run_once(cfg, slot, dry_run=args.dry_run, force=args.force))
    return 0


def cmd_run_due(args: argparse.Namespace) -> int:
    """What the scheduler calls: draft anything coming up, then act on anything due."""
    cfg = load_config()

    for slot in prepare_slots(cfg, load_state()):
        result = prepare_preview(cfg, slot)
        console.print(f"[cyan]Draft {slot}:[/] {result.status} - {result.reason}")

    slots = due_slots(cfg, load_state())
    if not slots:
        console.print("[dim]Nothing due right now.[/]")
        return 0

    for slot in slots:
        if cfg.mode == "preview":
            result = decide_preview(cfg, slot)
        else:
            result = run_once(cfg, slot, dry_run=args.dry_run)
        _show(result, heading=f"=== {slot} ===")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    run = sub.add_parser("run", help="write and publish one post")
    run.add_argument("--slot", default="")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--force", action="store_true", help="ignore the already-posted guard")
    run.set_defaults(func=cmd_run)

    due = sub.add_parser("run-due", help="handle whatever is due now (used by the scheduler)")
    due.add_argument("--dry-run", action="store_true")
    due.set_defaults(func=cmd_run_due)
