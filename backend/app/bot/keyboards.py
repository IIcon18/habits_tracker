"""Кнопки под сообщениями. callback_data: mark:{habitId}:full|mini, undo:{habitId}:{date}."""

import datetime as dt
import uuid

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.core.config import settings


def open_app_button() -> InlineKeyboardButton | None:
    if not settings.webapp_url:
        return None
    return InlineKeyboardButton(text="Открыть Каплю", web_app=WebAppInfo(url=settings.webapp_url))


def _rows(*rows: list[InlineKeyboardButton | None]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[r for r in ([b for b in row if b] for row in rows) if r])


def mark_keyboard(habit_id: uuid.UUID, *, two_misses: bool = False, with_open: bool = True) -> InlineKeyboardMarkup:
    full = InlineKeyboardButton(text="Сделал", callback_data=f"mark:{habit_id}:full")
    mini = InlineKeyboardButton(text="2 минуты", callback_data=f"mark:{habit_id}:mini")
    # После двух пропусков «2 минуты» — первой (design/09-bot.md).
    first_row = [mini, full] if two_misses else [full, mini]
    return _rows(first_row, [open_app_button() if with_open else None])


def undo_keyboard(habit_id: uuid.UUID, day: dt.date) -> InlineKeyboardMarkup:
    undo = InlineKeyboardButton(text="Отменить", callback_data=f"undo:{habit_id}:{day.isoformat()}")
    return _rows([undo, open_app_button()])


def start_keyboard() -> InlineKeyboardMarkup | None:
    button = open_app_button()
    return _rows([button]) if button else None
