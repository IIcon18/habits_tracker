"""Два напоминания: основное и «если не отмечено» со своим временем; разрешение писать."""

import datetime as dt

from aiogram.types import Chat, Message, WriteAccessAllowed
from aiogram.types import User as TgUser

from app.bot.handlers import write_access_allowed
from app.core.database import SessionLocal
from app.models import User
from app.schemas import ReminderIn
from app.services import habits, reminders

from .conftest import client_for
from .test_api import HABIT
from .test_bot import USER_ID, FakeBot, local, setup, tick

EVERY_DAY = [1, 2, 3, 4, 5, 6, 7]


async def test_custom_time_for_if_not_marked():
    await setup(evening_time=dt.time(13, 0))
    bot = FakeBot()
    assert await tick(bot, local(21, 5)) == 0  # больше не в 21:00
    assert await tick(bot, local(13, 10)) == 1
    assert "Сегодня ещё без капли" in bot.sent[0][1]


async def test_only_if_not_marked():
    """Основное выключено: пишем, только если к выбранному времени не отмечено."""
    await setup(morning=False, evening_time=dt.time(20, 0))
    bot = FakeBot()
    assert await tick(bot, local(7, 50)) == 0
    assert await tick(bot, local(20, 1)) == 1


async def test_moved_later_today_is_sent_again():
    user, habit = await setup()
    bot = FakeBot()
    assert await tick(bot, local(7, 46)) == 1
    async with SessionLocal() as session:
        user = await session.get(User, USER_ID)
        await reminders.set_reminder(
            session, user, habit.id, ReminderIn(time=dt.time(10, 0), days=EVERY_DAY), now=local(8, 0)
        )
    assert await tick(bot, local(10, 1)) == 1


async def test_moved_to_passed_time_is_not_sent_twice():
    user, habit = await setup()
    bot = FakeBot()
    assert await tick(bot, local(7, 46)) == 1
    async with SessionLocal() as session:
        user = await session.get(User, USER_ID)
        await reminders.set_reminder(
            session, user, habit.id, ReminderIn(time=dt.time(7, 30), days=EVERY_DAY), now=local(7, 50)
        )
    assert await tick(bot, local(7, 51)) == 0


async def test_reminder_api_and_validation():
    async with client_for(6006) as c:
        habit = (await c.post("/api/habits", json=HABIT)).json()
        url = f"/api/habits/{habit['id']}/reminder"
        r = await c.put(url, json={"time": "07:45", "days": EVERY_DAY, "morning": False, "evening": True, "eveningTime": "12:30"})
        assert r.status_code == 200, r.text
        assert r.json() == {"time": "07:45:00", "days": EVERY_DAY, "morning": False, "evening": True, "eveningTime": "12:30:00"}
        # Старый клиент без новых полей: всё как раньше.
        r = await c.put(url, json={"time": "07:45", "days": [1], "evening": True})
        assert r.json()["morning"] is True and r.json()["eveningTime"] == "21:00:00"
        # Ни одного напоминания или «если не отмечено» раньше основного — ошибка.
        assert (await c.put(url, json={"time": "07:45", "days": [1], "morning": False, "evening": False})).status_code == 422
        assert (await c.put(url, json={"time": "21:30", "days": [1], "eveningTime": "21:00"})).status_code == 422
        habits_list = (await c.get("/api/habits")).json()
        assert habits_list[0]["reminder"]["eveningTime"] == "21:00:00"


async def test_me_reports_write_access_and_bot_learns_permission():
    async with client_for(USER_ID) as c:
        assert (await c.get("/api/me")).json()["allowsWrite"] is None
    async with SessionLocal() as session:
        (await session.get(User, USER_ID)).allows_write = False
        await session.commit()

    message = Message(
        message_id=1,
        date=dt.datetime.now(dt.UTC),
        chat=Chat(id=USER_ID, type="private"),
        from_user=TgUser(id=USER_ID, is_bot=False, first_name="Илья"),
        write_access_allowed=WriteAccessAllowed(web_app_name="Капля"),
    )
    await write_access_allowed(message)
    async with client_for(USER_ID) as c:
        assert (await c.get("/api/me")).json()["allowsWrite"] is True


async def test_write_access_filter_matches_service_message():
    from aiogram import F

    message = Message(
        message_id=1,
        date=dt.datetime.now(dt.UTC),
        chat=Chat(id=1, type="private"),
        write_access_allowed=WriteAccessAllowed(),
    )
    assert F.write_access_allowed.resolve(message)
    assert not F.write_access_allowed.resolve(message.model_copy(update={"write_access_allowed": None}))


async def test_deleted_habit_reminder_is_gone_from_api():
    user, habit = await setup()
    async with SessionLocal() as session:
        await habits.delete_habit(session, await session.get(User, USER_ID), habit.id)
    assert await tick(FakeBot(), local(7, 46)) == 0
