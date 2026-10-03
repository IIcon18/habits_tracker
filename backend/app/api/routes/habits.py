import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.models import Habit
from app.schemas import HabitIn, HabitOut, HabitPatch
from app.services import habits

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get("", response_model=list[HabitOut])
async def list_habits(user: CurrentUser, session: SessionDep) -> list[Habit]:
    return await habits.list_habits(session, user)


@router.post("", response_model=HabitOut, status_code=status.HTTP_201_CREATED)
async def create_habit(body: HabitIn, user: CurrentUser, session: SessionDep) -> Habit:
    return await habits.create_habit(session, user, body)


@router.patch("/{habit_id}", response_model=HabitOut)
async def update_habit(habit_id: uuid.UUID, body: HabitPatch, user: CurrentUser, session: SessionDep) -> Habit:
    return await habits.update_habit(session, user, habit_id, body)


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit(habit_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Response:
    await habits.delete_habit(session, user, habit_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{habit_id}/pause", response_model=HabitOut)
async def pause_habit(habit_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Habit:
    return await habits.pause_habit(session, user, habit_id)


@router.post("/{habit_id}/resume", response_model=HabitOut)
async def resume_habit(habit_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Habit:
    return await habits.resume_habit(session, user, habit_id)
