"""Keep the cron block in post.yml in step with the config.

rewrite_cron() is pure text-in, text-out so it can be tested without files.
"""
from __future__ import annotations

import re
from pathlib import Path

from agent import paths
from agent.config import Config
from agent.schedule import cron_lines

WORKFLOW = Path(".github") / "workflows" / "post.yml"

class WorkflowError(ValueError):
    """post.yml is missing or not shaped the way we expect."""


def render_block(lines: list[str], indent: str) -> str:
    comment = f"{indent}# Generated from data/config.json - edit your schedule in the app.\n"
    items = "".join(f'{indent}- cron: "{line}"\n' for line in lines)
    return comment + items + "\n"


def _is_schedule_body(line: str) -> bool:
    """Lines that belong to the schedule block: cron items, comments, blank lines."""
    stripped = line.strip()
    return not stripped or stripped.startswith("#") or stripped.startswith("- cron:")


def rewrite_cron(yaml_text: str, lines: list[str]) -> str:
    """Replace the cron entries under `schedule:`, or add a schedule block if there is none."""
    rows = yaml_text.splitlines(keepends=True)

    for i, row in enumerate(rows):
        if row.strip() != "schedule:":
            continue

        end = i + 1
        while end < len(rows) and _is_schedule_body(rows[end]):
            end += 1

        body = rows[i + 1:end]
        first_cron = next((r for r in body if r.strip().startswith("- cron:")), None)
        schedule_indent = row[: len(row) - len(row.lstrip())]
        indent = (first_cron[: len(first_cron) - len(first_cron.lstrip())]
                  if first_cron else schedule_indent + "  ")

        return "".join(rows[: i + 1]) + render_block(lines, indent) + "".join(rows[end:])

    for i, row in enumerate(rows):
        if row.rstrip() == "on:":
            block = "  schedule:\n" + render_block(lines, "    ")
            return "".join(rows[: i + 1]) + block + "".join(rows[i + 1:])

    raise WorkflowError("post.yml has no top-level `on:` section to add a schedule to.")


def current_cron(yaml_text: str) -> list[str]:
    return re.findall(r'- cron:\s*"([^"]+)"', yaml_text)


def workflow_path() -> Path:
    return paths.ROOT / WORKFLOW


def apply(cfg: Config, path: Path | None = None) -> tuple[list[str], bool]:
    """Write the cron lines for `cfg` into post.yml. Returns (lines, changed)."""
    path = path or workflow_path()
    if not path.exists():
        raise WorkflowError(f"Could not find {path}.")

    before = path.read_text(encoding="utf-8")
    lines = cron_lines(cfg)
    after = rewrite_cron(before, lines)

    if after != before:
        path.write_text(after, encoding="utf-8", newline="\n")
    return lines, after != before
