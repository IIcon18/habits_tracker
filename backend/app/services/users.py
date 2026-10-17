import datetime as dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import TelegramUser
from app.models import User


def user_today(user: User) -> dt.date:
    """«Сегодня» в часовом поясе пользователя."""
    return dt.datetime.now(ZoneInfo(user.timezone)).date()


def valid_timezone(name: str | None) -> str | None:
    if not name:
        return None
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None
    return name


async def sync_user(session: AsyncSession, tg_user: TelegramUser, timezone: str | None) -> User:
    """Создаёт пользователя при первом входе и обновляет имя и часовой пояс."""
    timezone = valid_timezone(timezone)
    # При первом запуске приложение шлёт несколько запросов сразу (привычки и поток событий):
    # «найти, иначе создать» в двух запросах наперегонки дало бы дубль ключа и 500.
    await session.execute(
        insert(User)
        .values(id=tg_user.id, first_name=tg_user.first_name, timezone=timezone or settings.default_timezone)
        .on_conflict_do_nothing(index_elements=[User.id])
    )
    user = await session.get(User, tg_user.id)
    assert user is not None
    user.first_name = tg_user.first_name
    user.username = tg_user.username
    user.language_code = tg_user.language_code
    if timezone:
        user.timezone = timezone
    await session.commit()
    return user
