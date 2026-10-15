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


def current_message(habit: Habit, stats: HabitStats, today: dt.date, slot: Slot) -> tuple[str, InlineKeyboardMarkup]:
    """Сообщение по сегодняшнему состоянию: «засчитано», если отметка есть, иначе напоминание."""
    mark = next((m for m in habit.marks if m.date == today), None)
    if mark:
        return marked_message(habit, stats, mark.kind, today)
    return reminder_message(habit, stats, slot)


def message_slot(habit: Habit, today: dt.date) -> Slot:
    """Каким было сегодняшнее напоминание; если бот сегодня не писал — утреннее."""
    reminder = habit.reminder
    if reminder and reminder.message_on == today and reminder.message_slot == "evening":
        return "evening"
    return "morning"
