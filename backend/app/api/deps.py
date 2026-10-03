from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.security import InvalidInitData, TelegramUser, validate_init_data
from app.models import User
from app.services.users import sync_user

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
    x_timezone: Annotated[str | None, Header()] = None,
) -> User:
    """Пользователь запроса. Заголовки: `Authorization: tma <initData>`, `X-Timezone: Europe/Moscow`."""
    if authorization and authorization.startswith("tma "):
        try:
            tg_user = validate_init_data(
                authorization.removeprefix("tma "), settings.bot_token, settings.init_data_max_age_seconds
            )
        except InvalidInitData as e:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    elif settings.debug and settings.dev_user_id:
        tg_user = TelegramUser(id=settings.dev_user_id, first_name="Dev")
    else:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "нужен заголовок Authorization: tma <initData>")
    return await sync_user(session, tg_user, x_timezone)


CurrentUser = Annotated[User, Depends(current_user)]
