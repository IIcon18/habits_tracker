"""Таблицы — design/01-product.md, раздел «Привычка»."""

import datetime as dt
import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    # Telegram user id.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    first_name: Mapped[str] = mapped_column(String(256), default="")
    username: Mapped[str | None] = mapped_column(String(64))
    language_code: Mapped[str | None] = mapped_column(String(16))
    timezone: Mapped[str] = mapped_column(String(64))
    # Может ли бот писать пользователю; None — ещё не знаем (экран 8.4).
    allows_write: Mapped[bool | None]
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    habits: Mapped[list["Habit"]] = relationship(back_populates="user")


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

    user: Mapped[User] = relationship(back_populates="habits")
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


class Mark(Base):
    __tablename__ = "marks"
    __table_args__ = (
        UniqueConstraint("habit_id", "date", name="marks_one_per_day"),
        CheckConstraint("kind in ('full', 'mini')", name="mark_kind"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    habit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"))
    # Дата в часовом поясе пользователя.
    date: Mapped[dt.date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(8))
    at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))

    habit: Mapped[Habit] = relationship(back_populates="marks")


class Reminder(Base):
    __tablename__ = "reminders"

    habit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"), primary_key=True)
    time: Mapped[dt.time] = mapped_column(Time)
    # Дни недели 1 (пн) … 7 (вс).
    days: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    # Вечером в 21:00, если за день нет отметки.
    evening: Mapped[bool] = mapped_column(default=True)

    habit: Mapped[Habit] = relationship(back_populates="reminder")
