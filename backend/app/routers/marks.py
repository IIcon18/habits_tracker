import datetime as dt
import uuid

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from ..auth import CurrentUser
from ..deps import Session, get_owned_habit, user_today
from ..models import Mark
from ..schemas import MarkIn, MarkOut

router = APIRouter(prefix="/habits/{habit_id}/marks")


@router.put("/{day}", response_model=MarkOut)
async def put_mark(habit_id: uuid.UUID, day: dt.date, body: MarkIn, user: CurrentUser, session: Session) -> Mark:
    """Поставить отметку. Идемпотентно: повтор из офлайн-очереди не создаёт дубль."""
    habit = await get_owned_habit(session, user, habit_id)
    today = user_today(user)
    # Вчера — только для очереди без сети, отправленной уже после полуночи (экран 9.2).
    if day not in (today, today - dt.timedelta(days=1)) or day < habit.created_at:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "отметить можно только сегодня")
    if habit.status == "paused":
        raise HTTPException(status.HTTP_409_CONFLICT, "привычка на паузе")

    at = body.at or dt.datetime.now(dt.UTC)
    stmt = (
        insert(Mark)
        .values(habit_id=habit.id, date=day, kind=body.kind, at=at)
        .on_conflict_do_update(constraint="marks_one_per_day", set_={"kind": body.kind, "at": at})
        .returning(Mark)
        .execution_options(populate_existing=True)
    )
    mark = await session.scalar(stmt)
    await session.commit()
    return mark


@router.delete("/{day}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mark(habit_id: uuid.UUID, day: dt.date, user: CurrentUser, session: Session) -> Response:
    """Отменить отметку можно только в тот же день."""
    habit = await get_owned_habit(session, user, habit_id)
    if day != user_today(user):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "отменить можно только сегодняшнюю отметку")
    await session.execute(delete(Mark).where(Mark.habit_id == habit.id, Mark.date == day))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
