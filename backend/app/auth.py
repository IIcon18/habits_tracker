"""Авторизация Mini App: проверка подписи initData (https://core.telegram.org/bots/webapps)."""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Annotated
from urllib.parse import parse_qsl
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_session
from .models import User


class InvalidInitData(Exception):
    pass


@dataclass
class TelegramUser:
    id: int
    first_name: str = ""
    username: str | None = None
    language_code: str | None = None


def validate_init_data(init_data: str, bot_token: str, max_age: int, now: float | None = None) -> TelegramUser:
    """Проверяет подпись и свежесть initData, возвращает пользователя."""
    if not bot_token:
        raise InvalidInitData("BOT_TOKEN не задан")
    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InvalidInitData("нет hash")

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InvalidInitData("неверная подпись")

    try:
        auth_date = int(pairs["auth_date"])
    except (KeyError, ValueError) as e:
        raise InvalidInitData("нет auth_date") from e
    if (now or time.time()) - auth_date > max_age:
        raise InvalidInitData("initData просрочена")

    try:
        raw = json.loads(pairs["user"])
    except (KeyError, ValueError) as e:
        raise InvalidInitData("нет user") from e
    return TelegramUser(
        id=int(raw["id"]),
        first_name=raw.get("first_name", ""),
        username=raw.get("username"),
        language_code=raw.get("language_code"),
    )


def _valid_timezone(name: str | None) -> str | None:
    if not name:
        return None
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None
    return name


async def current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
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

    timezone = _valid_timezone(x_timezone)
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


CurrentUser = Annotated[User, Depends(current_user)]
