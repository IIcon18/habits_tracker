import datetime as dt
import uuid
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notify import notify_changed
from app.models import Reminder, User
from app.schemas import ReminderIn

from .habits import get_habit


async def get_reminder(session: AsyncSession, user: User, habit_id: uuid.UUID) -> Reminder | None:
    habit = await get_habit(session, user, habit_id)
    return habit.reminder


async def set_reminder(
    session: AsyncSession, user: User, habit_id: uuid.UUID, data: ReminderIn, now: dt.datetime | None = None
) -> Reminder:
    habit = await get_habit(session, user, habit_id)
    days = sorted(set(data.days))
    reminder = habit.reminder
    if reminder is None:
        reminder = habit.reminder = Reminder()
    else:
        # Сегодняшнее уже ушло, а время перенесли на ещё не наступившее — пусть придёт сегодня в новое время.
        local_now = (now or dt.datetime.now(dt.UTC)).astimezone(ZoneInfo(user.timezone)).time()
        if data.time != reminder.time and data.time > local_now:
            reminder.last_morning_on = None
        if data.evening_time != reminder.evening_time and data.evening_time > local_now:
            reminder.last_evening_on = None
    reminder.time = data.time
    reminder.days = days
    reminder.morning = data.morning
    reminder.evening = data.evening
    reminder.evening_time = data.evening_time
    await notify_changed(session, user.id)
    await session.commit()
    return reminder
