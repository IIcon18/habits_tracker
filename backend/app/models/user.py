import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .habit import Habit


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
