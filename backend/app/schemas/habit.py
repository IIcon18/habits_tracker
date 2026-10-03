import datetime as dt
import uuid
from typing import Literal

from .base import Schema, Text
from .mark import MarkOut
from .reminder import ReminderOut


class HabitIn(Schema):
    identity: Text
    full: Text
    mini: Text
    anchor: Text
    reward: Text | None = None


class HabitPatch(Schema):
    """Только переданные поля. Обязательные поля обнулить нельзя, награду — можно."""

    identity: Text | None = None
    full: Text | None = None
    mini: Text | None = None
    anchor: Text | None = None
    reward: Text | None = None


class PauseOut(Schema):
    start: dt.date
    end: dt.date | None


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
