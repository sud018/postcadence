"""Numbers about what has been posted, shaped for the dashboard charts.

Pure functions over State: no files, no network, no dates from the clock unless
you pass them in - so every chart is testable with a hand-made history.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from agent.state import State

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass
class Day:
    date: str          # "YYYY-MM-DD"
    posted: int
    failed: int
    skipped: int

    @property
    def weekday(self) -> str:
        return WEEKDAYS[date.fromisoformat(self.date).weekday()]

    @property
    def label(self) -> str:
        """'Mon 28 Sep' - what the tooltip and table show."""
        d = date.fromisoformat(self.date)
        return f"{self.weekday} {d.day} {d.strftime('%b')}"


def daily(state: State, today: str, days: int = 30) -> list[Day]:
    """One row per day for the last `days` days, oldest first, gaps filled with zeros.

    Empty days matter: a chart that skips them would make a quiet fortnight
    look like a busy week.
    """
    end = date.fromisoformat(today)
    rows = {
        (end - timedelta(days=offset)).isoformat(): Day(
            (end - timedelta(days=offset)).isoformat(), 0, 0, 0)
        for offset in range(days)
    }

    for entry in state.history:
        row = rows.get(entry.date)
        if row is None:
            continue                       # outside the window
        if entry.status == "posted":
            row.posted += 1
        elif entry.status == "failed":
            row.failed += 1
        elif entry.status == "skipped":
            row.skipped += 1

    return [rows[key] for key in sorted(rows)]


def by_slot(state: State, slots: list[str]) -> list[tuple[str, int]]:
    """Published posts per time slot, in schedule order.

    Your configured slots always appear (even at zero), followed by any old
    slots that still have history from before you changed the schedule.
    """
    counts: dict[str, int] = {slot: 0 for slot in sorted(slots)}
    for entry in state.history:
        if entry.status == "posted":
            counts[entry.slot] = counts.get(entry.slot, 0) + 1

    current = [(slot, counts[slot]) for slot in sorted(slots)]
    retired = sorted((slot, n) for slot, n in counts.items() if slot not in slots and n)
    return current + retired


def summary(rows: list[Day]) -> dict[str, int]:
    """Totals across the window, for the chart subtitle."""
    return {
        "posted": sum(r.posted for r in rows),
        "failed": sum(r.failed for r in rows),
        "skipped": sum(r.skipped for r in rows),
        "active_days": sum(1 for r in rows if r.posted),
    }


def nice_max(value: int) -> int:
    """Round the top of the axis up to a clean number: 3 -> 4, 7 -> 8, 11 -> 15."""
    for step in (1, 2, 4, 5, 8, 10, 15, 20, 25, 50, 100):
        if value <= step:
            return step
    return ((value + 99) // 100) * 100
