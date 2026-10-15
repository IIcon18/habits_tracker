"""Сообщение бота следует за отметками из приложения.

Когда отметку ставят или отменяют в Mini App, сегодняшнее напоминание в чате перерисовывается:
вместо «Сделал / 2 минуты» — «засчитано» с кнопкой «Отменить», и обратно.
Сигнал приходит через LISTEN/NOTIFY (app.core.notify) — от API и от самого бота.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.models import Habit, Reminder, User
from app.services.stats import habit_stats
from app.services.users import user_today

from .messages import Slot, current_message

log = logging.getLogger(__name__)


async def refresh_messages(session: AsyncSession, bot: Bot, user_id: int) -> int:
    """Перерисовывает сегодняшние напоминания пользователя. Возвращает число изменённых сообщений."""
    user = await session.get(User, user_id)
    if user is None:
        return 0
    today = user_today(user)
    reminders = await session.scalars(
        select(Reminder)
        .join(Reminder.habit)
        .where(
            Habit.user_id == user_id,
            Habit.status == "active",
            Habit.deleted_at.is_(None),
            Reminder.message_on == today,
            Reminder.message_id.is_not(None),
        )
        .options(
            selectinload(Reminder.habit).selectinload(Habit.marks),
            selectinload(Reminder.habit).selectinload(Habit.pauses),
        )
        .execution_options(populate_existing=True)
    )
    edited = 0
    for reminder in reminders:
        habit = reminder.habit
        slot: Slot = "evening" if reminder.message_slot == "evening" else "morning"
        text, markup = current_message(habit, habit_stats(habit, today), today, slot)
        try:
            await bot.edit_message_text(text, chat_id=user_id, message_id=reminder.message_id, reply_markup=markup)
        except TelegramBadRequest as e:
            # Сообщение уже в нужном виде (например, кнопку нажали в чате) — это нормально.
            if "message is not modified" in str(e):
                continue
            # Человек удалил сообщение — больше не трогаем.
            log.info("не удалось обновить сообщение %s: %s", reminder.message_id, e)
            reminder.message_id = None
        except TelegramAPIError:
            log.exception("не удалось обновить сообщение пользователю %s", user_id)
        else:
            edited += 1
    await session.commit()
    return edited


class MessageSync:
    """Обработчик уведомлений: по пользователю одна перерисовка за раз, изменения во время неё — ещё одна."""

    def __init__(self, bot: Bot, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._bot = bot
        self._sessions = session_factory
        self._running: dict[int, asyncio.Task[None]] = {}
        self._again: set[int] = set()

    def changed(self, user_id: int | None) -> None:
        # После переподключения к базе (None) догонять нечего: сообщение обновится при следующем изменении
        # или при нажатии кнопки в нём.
        if user_id is None:
            return
        if user_id in self._running:
            self._again.add(user_id)
            return
        self._running[user_id] = asyncio.create_task(self._run(user_id))

    async def _run(self, user_id: int) -> None:
        try:
            while True:
                self._again.discard(user_id)
                try:
                    async with self._sessions() as session:
                        await refresh_messages(session, self._bot, user_id)
                except Exception:
                    log.exception("ошибка обновления сообщений пользователя %s", user_id)
                if user_id not in self._again:
                    return
        finally:
            del self._running[user_id]
