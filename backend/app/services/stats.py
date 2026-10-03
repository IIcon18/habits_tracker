"""Серия, пропуски и голоса — порт frontend/src/lib/stats.ts, правила из design/01-product.md.

Голоса — все отметки; один пропуск не обнуляет серию, но и не добавляет к ней;
два пропуска подряд обнуляют серию; дни на паузе не считаются пропусками.
Меняешь правила здесь — поменяй и во фронтенде.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.models import Habit

DayState = Literal["full", "mini", "miss", "miss2", "today-empty", "before"]
MissState = Literal["none", "one", "two"]

ROW_LENGTH = 14


@dataclass
class Pause:
    start: date
    end: date | None  # None — пауза ещё идёт


@dataclass
class HabitStats:
    days: list[DayState]  # 14 дней, последний — сегодня
    votes: int
    streak: int
    marked_today: bool
    miss_state: MissState


def compute_stats(
    created_at: date, marks: dict[date, str], pauses: list[Pause], today: date
) -> HabitStats:
    def on_pause(d: date) -> bool:
        return any(p.start <= d and (p.end is None or d < p.end) for p in pauses)

    def tracked(d: date) -> bool:
        return d >= created_at and not on_pause(d)

    def miss(d: date) -> bool:
        return d < today and tracked(d) and d not in marks

    streak = 0
    miss_run = 0
    d = created_at
    while d < today:
        if tracked(d):
            if d in marks:
                streak += 1
                miss_run = 0
            else:
                miss_run += 1
                if miss_run >= 2:
                    streak = 0
        d += timedelta(days=1)

    marked_today = today in marks
    if marked_today:
        streak += 1

    yesterday = today - timedelta(days=1)
    day_before = today - timedelta(days=2)
    miss_state: MissState = "none"
    if not marked_today and miss(yesterday):
        miss_state = "two" if miss(day_before) else "one"

    days: list[DayState] = []
    for i in range(ROW_LENGTH - 1, -1, -1):
        d = today - timedelta(days=i)
        kind = marks.get(d)
        if kind:
            days.append("full" if kind == "full" else "mini")
        elif d == today:
            days.append("today-empty")
        elif not tracked(d):
            days.append("before")
        elif miss_state == "two" and d in (yesterday, day_before):
            days.append("miss2")
        else:
            days.append("miss")

    return HabitStats(days=days, votes=len(marks), streak=streak, marked_today=marked_today, miss_state=miss_state)


def habit_stats(habit: "Habit", today: date) -> HabitStats:
    """Статистика привычки из модели (отметки и паузы должны быть загружены)."""
    return compute_stats(
        habit.created_at,
        {m.date: m.kind for m in habit.marks},
        [Pause(start=p.start, end=p.end) for p in habit.pauses],
        today,
    )
