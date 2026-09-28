"""Analytics and chart geometry - built from hand-made histories, no clock."""
from __future__ import annotations

from agent import analytics
from agent.state import HistoryEntry, State
from web import charts


def entry(day: str, status: str = "posted", slot: str = "09:00") -> HistoryEntry:
    return HistoryEntry(date=day, slot=slot, topic="t", status=status)


def test_daily_fills_empty_days_with_zeros():
    rows = analytics.daily(State(history=[entry("2026-09-28")]), "2026-09-28", days=7)
    assert len(rows) == 7
    assert [r.posted for r in rows] == [0, 0, 0, 0, 0, 0, 1]
    assert rows[0].date == "2026-09-22"          # oldest first


def test_daily_counts_each_status_separately():
    state = State(history=[entry("2026-09-28"), entry("2026-09-28", "failed"),
                           entry("2026-09-28", "skipped"), entry("2026-09-28", slot="17:00")])
    today = analytics.daily(state, "2026-09-28", days=1)[0]
    assert (today.posted, today.failed, today.skipped) == (2, 1, 1)


def test_history_outside_the_window_is_ignored():
    rows = analytics.daily(State(history=[entry("2026-01-01")]), "2026-09-28", days=30)
    assert sum(r.posted for r in rows) == 0


def test_labels_read_like_a_calendar():
    row = analytics.daily(State(), "2026-09-28", days=1)[0]
    assert row.label == "Mon 28 Sep"


def test_by_slot_keeps_empty_slots_and_retired_ones():
    state = State(history=[entry("2026-09-01", slot="09:00"), entry("2026-09-02", slot="13:00")])
    assert analytics.by_slot(state, ["17:00", "09:00"]) == [("09:00", 1), ("17:00", 0), ("13:00", 1)]


def test_summary_counts_active_days():
    state = State(history=[entry("2026-09-27"), entry("2026-09-28"), entry("2026-09-28")])
    totals = analytics.summary(analytics.daily(state, "2026-09-28", days=30))
    assert totals["posted"] == 3
    assert totals["active_days"] == 2


def test_axis_tops_are_clean_numbers():
    assert [analytics.nice_max(n) for n in (0, 1, 3, 7, 11, 130)] == [1, 1, 4, 8, 15, 200]


# --- geometry ---------------------------------------------------------------

def test_taller_day_means_taller_column():
    state = State(history=[entry("2026-09-27"), entry("2026-09-28"), entry("2026-09-28", slot="17:00")])
    chart = charts.activity(analytics.daily(state, "2026-09-28", days=2))
    one, two = chart["columns"]
    assert two.height == 2 * one.height


def test_zero_days_draw_no_mark_but_keep_a_hover_target():
    chart = charts.activity(analytics.daily(State(), "2026-09-28", days=3))
    assert all(c.path == "" for c in chart["columns"])
    assert len(chart["columns"]) == 3
    assert chart["empty"] is True


def test_columns_stay_thin():
    assert charts.BAR <= 24 and charts.BAR < charts.SLOT


def test_today_is_always_labelled_and_labels_never_touch():
    chart = charts.activity(analytics.daily(State(), "2026-09-28", days=30))
    xs = [label["x"] for label in chart["labels"]]
    assert chart["labels"][-1]["text"] == "28 Sep"
    assert all(b - a >= 7 * charts.SLOT for a, b in zip(xs, xs[1:], strict=False))


def test_tooltip_mentions_failures_only_when_there_are_some():
    state = State(history=[entry("2026-09-28"), entry("2026-09-28", "failed")])
    [day] = analytics.daily(state, "2026-09-28", days=1)
    assert charts.activity([day])["columns"][0].tip == "Mon 28 Sep: 1 published, 1 failed"


def test_slot_bars_are_relative_to_the_busiest():
    bars = charts.slot_bars([("09:00", 10), ("17:00", 5)])
    assert [b["pct"] for b in bars] == [100.0, 50.0]
