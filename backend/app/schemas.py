"""Схемы API. Поля в JSON — camelCase, как во фронтенде (frontend/src/lib/types.ts)."""

import datetime as dt
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
MarkKind = Literal["full", "mini"]


class Schema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class MeOut(Schema):
    id: int
    first_name: str
    timezone: str
    today: dt.date


class PauseOut(Schema):
    start: dt.date
    end: dt.date | None


class MarkOut(Schema):
    date: dt.date
    kind: MarkKind
    at: dt.datetime


class ReminderIn(Schema):
    time: dt.time
    days: list[Annotated[int, Field(ge=1, le=7)]] = Field(min_length=1, max_length=7)
    evening: bool = True


class ReminderOut(ReminderIn):
    pass


class HabitIn(Schema):
    identity: Text
    full: Text
    mini: Text
    anchor: Text
    reward: Text | None = None


class HabitPatch(Schema):
    identity: Text | None = None
    full: Text | None = None
    mini: Text | None = None
    anchor: Text | None = None
    reward: Text | None = None


class HabitOut(Schema):
    id: uuid.UUID
    identity: str
    full: str
    mini: str
    anchor: str
    reward: str | None
    status: Literal["active", "paused"]
    created_at: dt.date
    pauses: list[PauseOut]
    marks: list[MarkOut]
    reminder: ReminderOut | None


class MarkIn(Schema):
    kind: MarkKind
    # Когда человек нажал кнопку; для офлайн-очереди может быть в прошлом.
    at: dt.datetime | None = None
