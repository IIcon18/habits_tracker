import datetime as dt

from .base import Schema


class MeOut(Schema):
    id: int
    first_name: str
    timezone: str
    # «Сегодня» в часовом поясе пользователя.
    today: dt.date
