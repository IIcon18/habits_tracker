"""Бот на тестовой базе: отметка из чата и планировщик напоминаний."""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage

from app.bot import actions
from app.bot.scheduler import send_due_reminders
from app.core.database import SessionLocal
from app.core.exceptions import InvalidInput
from app.core.security import TelegramUser
from app.models import Habit, Mark, User
from app.schemas import HabitIn, ReminderIn
from app.services import habits, marks, reminders
from app.services.users import sync_user, user_today

TZ = "Europe/Moscow"
USER_ID = 3003


class FakeBot:
    def __init__(self, fail: Exception | None = None):
        self.sent: list[tuple[int, str]] = []
        self.fail = fail

    async def send_message(self, chat_id: int, text: str, reply_markup=None):
        if self.fail:
            raise self.fail
        self.sent.append((chat_id, text))


async def setup(evening: bool = True, at: dt.time = dt.time(7, 45)) -> tuple[User, Habit]:
    async with SessionLocal() as session:
        user = await sync_user(session, TelegramUser(id=USER_ID, first_name="Илья"), TZ)
        habit = await habits.create_habit(
            session, user, HabitIn(identity="читает", full="читаю 30 минут", mini="одна страница", anchor="налью кофе")
        )
        await reminders.set_reminder(session, user, habit.id, ReminderIn(time=at, days=[1, 2, 3, 4, 5, 6, 7], evening=evening))
        return user, habit


def local(hour: int, minute: int) -> dt.datetime:
    today = dt.datetime.now(ZoneInfo(TZ)).date()
    return dt.datetime.combine(today, dt.time(hour, minute), tzinfo=ZoneInfo(TZ)).astimezone(dt.UTC)


async def tick(bot: FakeBot, now: dt.datetime) -> int:
    async with SessionLocal() as session:
        return await send_due_reminders(session, bot, now)


async def test_mark_and_undo_from_chat():
    _, habit = await setup()
    async with SessionLocal() as session:
        text, keyboard, toast = await actions.mark(session, USER_ID, habit.id, "full")
    assert "Сделал полностью — капля засчитана." in text
    assert toast == "Капля засчитана · +1 голос"
    assert keyboard.inline_keyboard[0][0].text == "Отменить"

    async with SessionLocal() as session:
        user = await session.get(User, USER_ID)
        today = user_today(user)
        assert (await session.get(Habit, habit.id)) is not None
        text, keyboard = await actions.undo(session, USER_ID, habit.id, today)
    assert "самое время" in text
    assert keyboard.inline_keyboard[0][0].text == "Сделал"

    async with SessionLocal() as session:
        with pytest.raises(InvalidInput):
            await actions.undo(session, USER_ID, habit.id, today - dt.timedelta(days=1))


async def test_morning_once_and_catch_up():
    await setup()
    bot = FakeBot()
    assert await tick(bot, local(7, 40)) == 0  # ещё рано
    assert await tick(bot, local(7, 50)) == 1  # догоняет в пределах часа
    assert await tick(bot, local(7, 51)) == 0  # второй раз не шлём
    assert "самое время" in bot.sent[0][1]
    assert bot.sent[0][0] == USER_ID


async def test_morning_too_late_is_skipped():
    await setup()
    assert await tick(FakeBot(), local(9, 0)) == 0


async def test_evening_only_without_mark():
    _, habit = await setup()
    bot = FakeBot()
    assert await tick(bot, local(21, 5)) == 1
    assert "Хватит и двух минут" in bot.sent[0][1]

    # Другой день с отметкой: вечернее не нужно.
    async with SessionLocal() as session:
        await session.execute(Mark.__table__.delete())
        reminder = (await habits.get_habit(session, await session.get(User, USER_ID), habit.id)).reminder
        reminder.last_evening_on = None
        await session.commit()
        await marks.put_mark(session, await session.get(User, USER_ID), habit.id, user_today(await session.get(User, USER_ID)), "mini")
    assert await tick(bot, local(21, 6)) == 0


async def test_evening_disabled():
    await setup(evening=False)
    assert await tick(FakeBot(), local(21, 5)) == 0


async def test_forbidden_marks_user_and_stops_sending():
    await setup()
    forbidden = TelegramForbiddenError(method=SendMessage(chat_id=USER_ID, text="x"), message="Forbidden: bot can't initiate conversation")
    assert await tick(FakeBot(fail=forbidden), local(7, 46)) == 0
    async with SessionLocal() as session:
        assert (await session.get(User, USER_ID)).allows_write is False
    # Вечером даже не пытаемся.
    bot = FakeBot()
    assert await tick(bot, local(21, 5)) == 0 and bot.sent == []


async def test_bot_button_after_mark_in_app_keeps_mark():
    """В приложении отметили «2 минуты», потом нажали «Сделал» в старом сообщении бота."""
    user, habit = await setup()
    async with SessionLocal() as session:
        await marks.put_mark(session, user, habit.id, user_today(user), "mini")
    async with SessionLocal() as session:
        text, keyboard, toast = await actions.mark(session, USER_ID, habit.id, "full")
    assert toast == "Сегодня уже отмечено"
    # Сообщение показывает настоящую отметку, а не нажатую кнопку.
    assert "Две минуты засчитаны." in text and "1 голос" in text
    assert keyboard.inline_keyboard[0][0].text == "Отменить"
    async with SessionLocal() as session:
        stored = (await habits.get_habit(session, user, habit.id)).marks
    assert [m.kind for m in stored] == ["mini"]
