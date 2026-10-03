"""Таблицы — design/01-product.md, раздел «Привычка». Импорт отсюда регистрирует все модели (нужно Alembic)."""

from .habit import Habit, HabitPause
from .mark import Mark
from .reminder import Reminder
from .user import User

__all__ = ["Habit", "HabitPause", "Mark", "Reminder", "User"]
