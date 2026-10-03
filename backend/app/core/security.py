"""Проверка подписи initData Telegram Mini App (https://core.telegram.org/bots/webapps)."""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


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
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
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
