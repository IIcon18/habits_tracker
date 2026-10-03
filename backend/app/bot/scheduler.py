"""Напоминания: раз в минуту смотрим, у кого по его часовому поясу подошло время.

Утреннее — во время из настроек, вечернее — в 21:00, если за день нет отметки.
Дата отправки запоминается в reminders.last_*_on, поэтому сообщение не уйдёт дважды,
а если бот лежал в нужную минуту, оно догонит в течение часа.
"""

import asyncio
import datetime as dt
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Habit, Reminder
from app.services.stats import habit_stats

from .messages import Slot, reminder_message

log = logging.getLogger(__name__)

EVENING_AT = dt.time(21, 0)
CATCH_UP = dt.timedelta(hours=1)


def _in_window(local_now: dt.datetime, at: dt.time) -> bool:
    start = dt.datetime.combine(local_now.date(), at, tzinfo=local_now.tzinfo)
    return dt.timedelta(0) <= local_now - start < CATCH_UP


def due_slot(reminder: Reminder, local_now: dt.datetime) -> Slot | None:
    """Какое напоминание пора отправить сейчас (по местному времени пользователя)."""
    today = local_now.date()
    if local_now.isoweekday() not in reminder.days:
        return None
    if reminder.last_morning_on != today and _in_window(local_now, reminder.time):
        return "morning"
    if reminder.evening and reminder.last_evening_on != today and _in_window(local_now, EVENING_AT):
        return "evening"
    return None


async def send_due_reminders(session: AsyncSession, bot: Bot, now: dt.datetime | None = None) -> int:
    """Отправляет подошедшие напоминания, возвращает число отправленных."""
    now = now or dt.datetime.now(dt.UTC)
    reminders = await session.scalars(
        select(Reminder)
        .join(Reminder.habit)
        .where(Habit.status == "active", Habit.deleted_at.is_(None))
        .options(
            selectinload(Reminder.habit).selectinload(Habit.marks),
            selectinload(Reminder.habit).selectinload(Habit.pauses),
            selectinload(Reminder.habit).selectinload(Habit.user),
        )
    )
    sent = 0
    for reminder in reminders:
        habit = reminder.habit
        user = habit.user
        local_now = now.astimezone(ZoneInfo(user.timezone))
        slot = due_slot(reminder, local_now)
        if slot is None:
            continue

        today = local_now.date()
        reminder.last_morning_on = today if slot == "morning" else reminder.last_morning_on
        reminder.last_evening_on = today if slot == "evening" else reminder.last_evening_on
        # Утреннее в 21:00 заменяет вечернее — два сообщения подряд не шлём.
        if slot == "morning" and _in_window(local_now, EVENING_AT):
            reminder.last_evening_on = today

        stats = habit_stats(habit, today)
        if stats.marked_today or user.allows_write is False:
            continue
        text, keyboard = reminder_message(habit, stats, slot)
        try:
            await bot.send_message(user.id, text, reply_markup=keyboard)
        except TelegramForbiddenError:
            # Пользователь не запускал бота или заблокировал его — экран 8.4 в приложении.
            user.allows_write = False
        except TelegramAPIError:
            log.exception("не удалось отправить напоминание пользователю %s", user.id)
        else:
            user.allows_write = True
            sent += 1
    await session.commit()
    return sent


async def run_scheduler(bot: Bot, session_factory) -> None:
    """Бесконечный цикл: проверка в начале каждой минуты."""
    while True:
        try:
            async with session_factory() as session:
                sent = await send_due_reminders(session, bot)
            if sent:
                log.info("отправлено напоминаний: %s", sent)
        except Exception:
            log.exception("ошибка планировщика напоминаний")
        now = dt.datetime.now()
        await asyncio.sleep(60 - now.second - now.microsecond / 1_000_000)
