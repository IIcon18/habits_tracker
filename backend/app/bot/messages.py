"""Какое сообщение показать по привычке: напоминание, «два пропуска» или «засчитано»."""

import datetime as dt
from typing import Literal

from aiogram.types import InlineKeyboardMarkup

from app.models import Habit
from app.services.stats import HabitStats

from . import keyboards, texts

Slot = Literal["morning", "evening"]


def reminder_message(habit: Habit, stats: HabitStats, slot: Slot) -> tuple[str, InlineKeyboardMarkup]:
    if stats.miss_state == "two":
        return texts.two_misses(habit, stats), keyboards.mark_keyboard(habit.id, two_misses=True)
    if slot == "evening":
        # На эталоне 8.2 у вечернего сообщения только кнопки отметки.
        return texts.evening(habit, stats), keyboards.mark_keyboard(habit.id, with_open=False)
    return texts.morning(habit, stats), keyboards.mark_keyboard(habit.id)


def marked_message(habit: Habit, stats: HabitStats, kind: str, day: dt.date) -> tuple[str, InlineKeyboardMarkup]:
    return texts.marked(habit, stats, kind), keyboards.undo_keyboard(habit.id, day)
