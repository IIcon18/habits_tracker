import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import InvalidInput, NotFound
from app.models import Habit, HabitPause, User
from app.schemas import HabitIn, HabitPatch

from .users import user_today


def _habit_query():
    # populate_existing: после изменений в той же сессии отдаём свежие отметки и паузы.
    return (
        select(Habit)
        .options(selectinload(Habit.marks), selectinload(Habit.pauses), selectinload(Habit.reminder))
        .execution_options(populate_existing=True)
    )


async def list_habits(session: AsyncSession, user: User) -> list[Habit]:
    result = await session.scalars(
        _habit_query()
        .where(Habit.user_id == user.id, Habit.deleted_at.is_(None))
        .order_by(Habit.created_at, Habit.id)
    )
    return list(result)


async def get_habit(session: AsyncSession, user: User, habit_id: uuid.UUID) -> Habit:
    """Привычка пользователя; чужая или удалённая — NotFound."""
    habit = await session.scalar(
        _habit_query().where(Habit.id == habit_id, Habit.user_id == user.id, Habit.deleted_at.is_(None))
    )
    if habit is None:
        raise NotFound("привычка не найдена")
    return habit


async def create_habit(session: AsyncSession, user: User, data: HabitIn) -> Habit:
    habit = Habit(user_id=user.id, status="active", created_at=user_today(user), **data.model_dump())
    session.add(habit)
    await session.commit()
    return await get_habit(session, user, habit.id)


async def update_habit(session: AsyncSession, user: User, habit_id: uuid.UUID, data: HabitPatch) -> Habit:
    habit = await get_habit(session, user, habit_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None and field != "reward":
            raise InvalidInput(f"{field} не может быть пустым")
        setattr(habit, field, value)
    await session.commit()
    return await get_habit(session, user, habit_id)


async def delete_habit(session: AsyncSession, user: User, habit_id: uuid.UUID) -> None:
    habit = await get_habit(session, user, habit_id)
    habit.deleted_at = dt.datetime.now(dt.UTC)
    await session.commit()


async def pause_habit(session: AsyncSession, user: User, habit_id: uuid.UUID) -> Habit:
    habit = await get_habit(session, user, habit_id)
    if habit.status != "paused":
        habit.status = "paused"
        habit.pauses.append(HabitPause(start=user_today(user)))
        await session.commit()
    return await get_habit(session, user, habit_id)


async def resume_habit(session: AsyncSession, user: User, habit_id: uuid.UUID) -> Habit:
    habit = await get_habit(session, user, habit_id)
    if habit.status == "paused":
        habit.status = "active"
        today = user_today(user)
        for pause in habit.pauses:
            if pause.end is None:
                pause.end = today
        await session.commit()
    return await get_habit(session, user, habit_id)
