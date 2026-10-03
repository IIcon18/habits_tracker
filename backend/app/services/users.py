import datetime as dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
    user = await session.get(User, tg_user.id)
    if user is None:
        user = User(id=tg_user.id, timezone=timezone or settings.default_timezone)
        session.add(user)
    user.first_name = tg_user.first_name
    user.username = tg_user.username
    user.language_code = tg_user.language_code
    if timezone:
        user.timezone = timezone
    await session.commit()
    return user
