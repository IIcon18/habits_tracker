import datetime as dt
from typing import Annotated

from pydantic import Field

from .base import Schema

Weekday = Annotated[int, Field(ge=1, le=7)]


class ReminderIn(Schema):
    time: dt.time
    # Дни недели 1 (пн) … 7 (вс).
    days: list[Weekday] = Field(min_length=1, max_length=7)
    # Вечером в 21:00 мягко напомнить, если за день нет отметки.
    evening: bool = True


class ReminderOut(ReminderIn):
    pass
