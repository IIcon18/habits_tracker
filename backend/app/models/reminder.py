import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, Time
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .habit import Habit


class Reminder(Base):
    __tablename__ = "reminders"

    habit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"), primary_key=True)
    time: Mapped[dt.time] = mapped_column(Time)
    # Дни недели 1 (пн) … 7 (вс).
    days: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    # Вечером в 21:00, если за день нет отметки.
    evening: Mapped[bool] = mapped_column(default=True)
    # Даты (в поясе пользователя), когда бот уже отправил напоминание, — чтобы не слать дважды.
    last_morning_on: Mapped[dt.date | None] = mapped_column(Date)
    last_evening_on: Mapped[dt.date | None] = mapped_column(Date)

    habit: Mapped["Habit"] = relationship(back_populates="reminder")
