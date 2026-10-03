import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .mark import Mark
    from .reminder import Reminder
    from .user import User


class Habit(Base):
    __tablename__ = "habits"
    __table_args__ = (CheckConstraint("status in ('active', 'paused')", name="habit_status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Окончание идентичности: «читает».
    identity: Mapped[str] = mapped_column(Text)
    full: Mapped[str] = mapped_column(Text)
    mini: Mapped[str] = mapped_column(Text)
    # Якорь без префикса «После того как».
    anchor: Mapped[str] = mapped_column(Text)
    reward: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[dt.date] = mapped_column(Date)
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="habits")
    marks: Mapped[list["Mark"]] = relationship(
        back_populates="habit", cascade="all, delete-orphan", order_by="Mark.date"
    )
    pauses: Mapped[list["HabitPause"]] = relationship(
        back_populates="habit", cascade="all, delete-orphan", order_by="HabitPause.start"
    )
    reminder: Mapped["Reminder | None"] = relationship(back_populates="habit", cascade="all, delete-orphan")


class HabitPause(Base):
    """Интервал паузы: дни в [start, end) не считаются пропусками. end=None — пауза идёт."""

    __tablename__ = "habit_pauses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    habit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"), index=True)
    start: Mapped[dt.date] = mapped_column(Date)
    end: Mapped[dt.date | None] = mapped_column(Date)

    habit: Mapped[Habit] = relationship(back_populates="pauses")
