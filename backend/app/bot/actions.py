"""Отметка и отмена из чата — через те же сервисы, что и API."""

import datetime as dt
import uuid

from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFound
from app.models import User
from app.schemas import MarkKind
from app.services import habits, marks
from app.services.stats import habit_stats
from app.services.users import user_today

from . import texts
from .messages import marked_message, reminder_message


async def _user(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFound("сначала открой Каплю")
    return user


async def mark(
    session: AsyncSession, user_id: int, habit_id: uuid.UUID, kind: MarkKind
) -> tuple[str, InlineKeyboardMarkup, str]:
    """Возвращает текст, кнопки и всплывающую подсказку.

    Сообщение в чате не знает об отметках из приложения: если сегодня уже отмечено,
    отметку не трогаем и только показываем, как есть, — иначе «Сделал» молча заменил бы «2 минуты».
    """
    user = await _user(session, user_id)
    today = user_today(user)
    habit = await habits.get_habit(session, user, habit_id)
    existing = next((m for m in habit.marks if m.date == today), None)
    if existing:
        stats = habit_stats(habit, today)
        return (*marked_message(habit, stats, existing.kind, today), texts.ALREADY_MARKED_TOAST)
    await marks.put_mark(session, user, habit_id, today, kind)
    habit = await habits.get_habit(session, user, habit_id)
    return (*marked_message(habit, habit_stats(habit, today), kind, today), texts.MARKED_TOAST)


async def undo(
    session: AsyncSession, user_id: int, habit_id: uuid.UUID, day: dt.date
) -> tuple[str, InlineKeyboardMarkup]:
    """Отменить можно только в тот же день — иначе сервис бросит InvalidInput."""
    user = await _user(session, user_id)
    await marks.delete_mark(session, user, habit_id, day)
    habit = await habits.get_habit(session, user, habit_id)
    return reminder_message(habit, habit_stats(habit, user_today(user)), "morning")
