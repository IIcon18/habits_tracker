import datetime as dt
import uuid
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .db import get_session
from .models import Habit, User

Session = Annotated[AsyncSession, Depends(get_session)]


def user_today(user: User) -> dt.date:
    """«Сегодня» в часовом поясе пользователя."""
    return dt.datetime.now(ZoneInfo(user.timezone)).date()


def habit_query():
    # populate_existing: после изменений в той же сессии отдаём свежие отметки и паузы.
    return (
        select(Habit)
        .options(selectinload(Habit.marks), selectinload(Habit.pauses), selectinload(Habit.reminder))
        .execution_options(populate_existing=True)
    )


async def get_owned_habit(session: AsyncSession, user: User, habit_id: uuid.UUID) -> Habit:
    habit = await session.scalar(
        habit_query().where(Habit.id == habit_id, Habit.user_id == user.id, Habit.deleted_at.is_(None))
    )
    if habit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "привычка не найдена")
    return habit
