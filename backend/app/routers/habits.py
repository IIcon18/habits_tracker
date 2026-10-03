import datetime as dt
import uuid

from fastapi import APIRouter, HTTPException, Response, status

from ..auth import CurrentUser
from ..deps import Session, get_owned_habit, habit_query, user_today
from ..models import Habit, HabitPause
from ..schemas import HabitIn, HabitOut, HabitPatch

router = APIRouter(prefix="/habits")


@router.get("", response_model=list[HabitOut])
async def list_habits(user: CurrentUser, session: Session) -> list[Habit]:
    result = await session.scalars(
        habit_query().where(Habit.user_id == user.id, Habit.deleted_at.is_(None)).order_by(Habit.created_at, Habit.id)
    )
    return list(result)


@router.post("", response_model=HabitOut, status_code=status.HTTP_201_CREATED)
async def create_habit(body: HabitIn, user: CurrentUser, session: Session) -> Habit:
    habit = Habit(user_id=user.id, status="active", created_at=user_today(user), **body.model_dump())
    session.add(habit)
    await session.commit()
    return await get_owned_habit(session, user, habit.id)


@router.patch("/{habit_id}", response_model=HabitOut)
async def update_habit(habit_id: uuid.UUID, body: HabitPatch, user: CurrentUser, session: Session) -> Habit:
    habit = await get_owned_habit(session, user, habit_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        # Обязательные поля нельзя обнулить; награду — можно.
        if value is None and field != "reward":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{field} не может быть пустым")
        setattr(habit, field, value)
    await session.commit()
    return await get_owned_habit(session, user, habit_id)


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit(habit_id: uuid.UUID, user: CurrentUser, session: Session) -> Response:
    habit = await get_owned_habit(session, user, habit_id)
    habit.deleted_at = dt.datetime.now(dt.UTC)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{habit_id}/pause", response_model=HabitOut)
async def pause_habit(habit_id: uuid.UUID, user: CurrentUser, session: Session) -> Habit:
    habit = await get_owned_habit(session, user, habit_id)
    if habit.status != "paused":
        habit.status = "paused"
        habit.pauses.append(HabitPause(start=user_today(user)))
        await session.commit()
    return await get_owned_habit(session, user, habit_id)


@router.post("/{habit_id}/resume", response_model=HabitOut)
async def resume_habit(habit_id: uuid.UUID, user: CurrentUser, session: Session) -> Habit:
    habit = await get_owned_habit(session, user, habit_id)
    if habit.status == "paused":
        habit.status = "active"
        today = user_today(user)
        for pause in habit.pauses:
            if pause.end is None:
                pause.end = today
        await session.commit()
    return await get_owned_habit(session, user, habit_id)
