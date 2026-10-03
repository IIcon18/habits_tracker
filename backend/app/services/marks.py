import datetime as dt
import uuid

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, InvalidInput
from app.models import Mark, User
from app.schemas import MarkKind

from .habits import get_habit
from .users import user_today


async def put_mark(
    session: AsyncSession,
    user: User,
    habit_id: uuid.UUID,
    day: dt.date,
    kind: MarkKind,
    at: dt.datetime | None = None,
) -> Mark:
    """Поставить отметку. Идемпотентно: повтор из офлайн-очереди не создаёт дубль."""
    habit = await get_habit(session, user, habit_id)
    today = user_today(user)
    # Вчера — только для очереди без сети, отправленной уже после полуночи (экран 9.2).
    if day not in (today, today - dt.timedelta(days=1)) or day < habit.created_at:
        raise InvalidInput("отметить можно только сегодня")
    if habit.status == "paused":
        raise Conflict("привычка на паузе")

    at = at or dt.datetime.now(dt.UTC)
    stmt = (
        insert(Mark)
        .values(habit_id=habit.id, date=day, kind=kind, at=at)
        .on_conflict_do_update(constraint="marks_one_per_day", set_={"kind": kind, "at": at})
        .returning(Mark)
        .execution_options(populate_existing=True)
    )
    mark = await session.scalar(stmt)
    await session.commit()
    return mark


async def delete_mark(session: AsyncSession, user: User, habit_id: uuid.UUID, day: dt.date) -> None:
    """Отменить отметку можно только в тот же день."""
    habit = await get_habit(session, user, habit_id)
    if day != user_today(user):
        raise InvalidInput("отменить можно только сегодняшнюю отметку")
    await session.execute(delete(Mark).where(Mark.habit_id == habit.id, Mark.date == day))
    await session.commit()
