import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, String, Time, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .habit import Habit


class Reminder(Base):
    """Два напоминания, оба — только если сегодня ещё не отмечено.

    Основное (morning) — в time, обычно сразу после якоря. «Если не отмечено» (evening) — в evening_time,
    мягко про две минуты. Включено хотя бы одно; если оба — evening_time позже time.
    """

    __tablename__ = "reminders"

    habit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"), primary_key=True)
    time: Mapped[dt.time] = mapped_column(Time)
    # Дни недели 1 (пн) … 7 (вс), для обоих напоминаний.
    days: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    morning: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    evening: Mapped[bool] = mapped_column(default=True)
    evening_time: Mapped[dt.time] = mapped_column(Time, default=dt.time(21, 0), server_default=text("'21:00'"))
    # Даты (в поясе пользователя), когда бот уже отправил напоминание, — чтобы не слать дважды.
    last_morning_on: Mapped[dt.date | None] = mapped_column(Date)
    last_evening_on: Mapped[dt.date | None] = mapped_column(Date)
    # Последнее напоминание в чате: его бот перерисовывает, когда отметку ставят или отменяют в приложении.
    message_id: Mapped[int | None] = mapped_column(BigInteger)
    message_on: Mapped[dt.date | None] = mapped_column(Date)
    message_slot: Mapped[str | None] = mapped_column(String(8))

    habit: Mapped["Habit"] = relationship(back_populates="reminder")
