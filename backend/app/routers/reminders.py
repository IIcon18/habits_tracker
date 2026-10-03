import uuid

from fastapi import APIRouter

from ..auth import CurrentUser
from ..deps import Session, get_owned_habit
from ..models import Reminder
from ..schemas import ReminderIn, ReminderOut

router = APIRouter(prefix="/habits/{habit_id}/reminder")


@router.get("", response_model=ReminderOut | None)
async def get_reminder(habit_id: uuid.UUID, user: CurrentUser, session: Session) -> Reminder | None:
    habit = await get_owned_habit(session, user, habit_id)
    return habit.reminder


@router.put("", response_model=ReminderOut)
async def put_reminder(habit_id: uuid.UUID, body: ReminderIn, user: CurrentUser, session: Session) -> Reminder:
    habit = await get_owned_habit(session, user, habit_id)
    days = sorted(set(body.days))
    if habit.reminder is None:
        habit.reminder = Reminder(time=body.time, days=days, evening=body.evening)
    else:
        habit.reminder.time = body.time
        habit.reminder.days = days
        habit.reminder.evening = body.evening
    await session.commit()
    return habit.reminder
