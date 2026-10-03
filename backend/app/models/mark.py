import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .habit import Habit


class Mark(Base):
    """Отметка: одна на привычку в день."""

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

    habit: Mapped["Habit"] = relationship(back_populates="marks")
