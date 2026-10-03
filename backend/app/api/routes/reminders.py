import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.models import Reminder
from app.schemas import ReminderIn, ReminderOut
from app.services import reminders

router = APIRouter(prefix="/habits/{habit_id}/reminder", tags=["reminders"])


@router.get("", response_model=ReminderOut | None)
async def get_reminder(habit_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Reminder | None:
    return await reminders.get_reminder(session, user, habit_id)


@router.put("", response_model=ReminderOut)
async def put_reminder(habit_id: uuid.UUID, body: ReminderIn, user: CurrentUser, session: SessionDep) -> Reminder:
    return await reminders.set_reminder(session, user, habit_id, body)
