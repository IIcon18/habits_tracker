import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Reminder, User
from app.schemas import ReminderIn

from .habits import get_habit


async def get_reminder(session: AsyncSession, user: User, habit_id: uuid.UUID) -> Reminder | None:
    habit = await get_habit(session, user, habit_id)
    return habit.reminder


async def set_reminder(session: AsyncSession, user: User, habit_id: uuid.UUID, data: ReminderIn) -> Reminder:
    habit = await get_habit(session, user, habit_id)
    days = sorted(set(data.days))
    if habit.reminder is None:
        habit.reminder = Reminder(time=data.time, days=days, evening=data.evening)
    else:
        habit.reminder.time = data.time
        habit.reminder.days = days
        habit.reminder.evening = data.evening
    await session.commit()
    return habit.reminder
