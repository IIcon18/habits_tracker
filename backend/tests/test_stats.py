"""Правила серии из design/01-product.md — те же сценарии, что в демо фронтенда."""

from datetime import date, timedelta

from app.stats import Pause, compute_stats

TODAY = date(2026, 10, 2)


def habit(pattern: str, today_kind: str | None = None):
    """pattern — дни с начала привычки до вчера: d сделал, m две минуты, x пропуск."""
    start = TODAY - timedelta(days=len(pattern))
    marks = {start + timedelta(days=i): ("full" if ch == "d" else "mini") for i, ch in enumerate(pattern) if ch != "x"}
    if today_kind:
        marks[TODAY] = today_kind
    return start, marks


def test_one_miss_does_not_reset():
    start, marks = habit("ddxdd")
    s = compute_stats(start, marks, [], TODAY)
    assert s.streak == 4
    assert s.miss_state == "none"


def test_two_misses_reset_streak():
    start, marks = habit("dddxxdd")
    assert compute_stats(start, marks, [], TODAY).streak == 2


def test_yesterday_miss():
    start, marks = habit("dddx")
    s = compute_stats(start, marks, [], TODAY)
    assert s.miss_state == "one"
    assert s.streak == 3
    assert s.days[-2:] == ["miss", "today-empty"]


def test_two_misses_state_and_amber_cells():
    start, marks = habit("dddxx")
    s = compute_stats(start, marks, [], TODAY)
    assert s.miss_state == "two"
    assert s.streak == 0
    assert s.days[-3:] == ["miss2", "miss2", "today-empty"]


def test_mark_after_two_misses_starts_from_one():
    start, marks = habit("dddxx", today_kind="mini")
    s = compute_stats(start, marks, [], TODAY)
    assert s.streak == 1
    assert s.miss_state == "none"
    assert s.days[-1] == "mini"


def test_votes_count_full_and_mini():
    start, marks = habit("dmxdm", today_kind="full")
    assert compute_stats(start, marks, [], TODAY).votes == 5


def test_new_habit():
    s = compute_stats(TODAY, {}, [], TODAY)
    assert s.votes == 0
    assert s.streak == 0
    assert s.days == ["before"] * 13 + ["today-empty"]


def test_pause_days_are_not_misses():
    # 3 дня отметок, 5 дней паузы, 1 отметка после возврата.
    start, marks = habit("dddxxxxxd")
    pause = Pause(start=start + timedelta(days=3), end=start + timedelta(days=8))
    s = compute_stats(start, marks, [pause], TODAY)
    assert s.streak == 4
    assert s.miss_state == "none"
    assert s.days[-7:-2] == ["before"] * 5
