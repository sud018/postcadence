"""Turn analytics rows into SVG geometry, so templates only place shapes.

Doing the arithmetic here (not in Jinja) keeps it testable: a test can check
that a 3-post day is taller than a 1-post day without parsing any SVG.
"""
from __future__ import annotations

from dataclasses import dataclass

from agent.analytics import Day, nice_max

# Chart frame, in SVG user units (the viewBox scales it to the card width).
SLOT = 24          # horizontal room per day
BAR = 14           # column thickness - capped well under the slot, the rest is air
RADIUS = 4         # rounded data-end; the baseline end stays square
PLOT_H = 140       # height of the plotting area
LEFT = 28          # room for the y-axis numbers
TOP = 10
BOTTOM = 34        # room for the failure marks and date labels


@dataclass
class Column:
    x: float
    y: float
    height: float
    path: str
    hit_x: float
    day: Day
    tip: str


def column_path(x: float, y: float, width: float, height: float, base: float) -> str:
    """A column with a rounded top and a square bottom."""
    if height <= 0:
        return ""
    r = min(RADIUS, height, width / 2)
    return (f"M{x:.1f},{base:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
            f"H{x + width - r:.1f} Q{x + width:.1f},{y:.1f} {x + width:.1f},{y + r:.1f} "
            f"V{base:.1f} Z")


def _tip(day: Day) -> str:
    parts = [f"{day.posted} published"]
    if day.failed:
        parts.append(f"{day.failed} failed")
    if day.skipped:
        parts.append(f"{day.skipped} skipped")
    return f"{day.label}: " + ", ".join(parts)


def activity(rows: list[Day]) -> dict:
    """Everything the 30-day column chart needs."""
    top = nice_max(max((r.posted for r in rows), default=0) or 1)
    base = TOP + PLOT_H
    width = LEFT + SLOT * len(rows)

    columns = []
    for i, day in enumerate(rows):
        x = LEFT + i * SLOT + (SLOT - BAR) / 2
        height = PLOT_H * day.posted / top
        y = base - height
        columns.append(Column(x=x, y=y, height=height,
                              path=column_path(x, y, BAR, height, base),
                              hit_x=LEFT + i * SLOT, day=day, tip=_tip(day)))

    ticks = [{"value": v, "y": base - PLOT_H * v / top} for v in _tick_values(top)]

    # today, then every 7th day counting back - so the last two labels never collide
    label_at = set(range(len(rows) - 1, -1, -7))
    labels = [{"x": LEFT + i * SLOT + SLOT / 2, "text": rows[i].label.split(" ", 1)[1]}
              for i in sorted(label_at) if rows]

    return {
        "width": width,
        "height": TOP + PLOT_H + BOTTOM,
        "base": base,
        "left": LEFT,
        "slot": SLOT,
        "columns": columns,
        "ticks": ticks,
        "labels": labels,
        "fail_y": base + 12,
        "label_y": base + 28,
        "empty": all(r.posted == 0 and r.failed == 0 for r in rows),
    }


def _tick_values(top: int) -> list[int]:
    """0, the top, and one clean midpoint when there is room for it."""
    if top <= 1:
        return [0, 1]
    mid = top // 2
    return [0, mid, top] if mid * 2 == top else [0, top]


def slot_bars(counts: list[tuple[str, int]]) -> list[dict]:
    """Horizontal bars as percentages of the busiest slot."""
    peak = max((n for _, n in counts), default=0) or 1
    return [{"slot": slot, "count": n, "pct": round(100 * n / peak, 1)} for slot, n in counts]
