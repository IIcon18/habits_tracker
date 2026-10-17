import datetime as dt
from typing import Annotated

from pydantic import Field, model_validator

from .base import Schema

Weekday = Annotated[int, Field(ge=1, le=7)]


class ReminderIn(Schema):
    # Основное напоминание: в это время, если ещё не отмечено.
    time: dt.time
    # Дни недели 1 (пн) … 7 (вс).
    days: list[Weekday] = Field(min_length=1, max_length=7)
    morning: bool = True
    # «Если не отмечено» — ещё раз, мягко про две минуты.
    evening: bool = True
    evening_time: dt.time = dt.time(21, 0)

    @model_validator(mode="after")
    def check_times(self) -> "ReminderIn":
        if not (self.morning or self.evening):
            raise ValueError("включи хотя бы одно напоминание")
        if self.morning and self.evening and self.evening_time <= self.time:
            raise ValueError("«если не отмечено» должно быть позже основного напоминания")
        return self


class ReminderOut(Schema):
    time: dt.time
    days: list[int]
    morning: bool
    evening: bool
    evening_time: dt.time
