import datetime as dt
from typing import Literal

from .base import Schema

MarkKind = Literal["full", "mini"]


class MarkIn(Schema):
    kind: MarkKind
    # Когда человек нажал кнопку; для офлайн-очереди может быть в прошлом.
    at: dt.datetime | None = None


class MarkOut(Schema):
    date: dt.date
    kind: MarkKind
    at: dt.datetime
