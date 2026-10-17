import datetime as dt

from .base import Schema


class MeOut(Schema):
    id: int
    first_name: str
    timezone: str
    # «Сегодня» в часовом поясе пользователя.
    today: dt.date
    # Может ли бот писать: None — ещё не знаем, False — Telegram отказал (экран 8.4).
    allows_write: bool | None
