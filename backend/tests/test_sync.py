"""Синхронизация приложения и бота: изменение в одном месте сразу видно в другом."""

import asyncio
import contextlib

from app.api.routes.events import Broker, broker, event_stream
from app.bot.sync import MessageSync, refresh_messages
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.notify import asyncpg_dsn, listen
from app.models import User
from app.services import marks
from app.services.users import user_today

from .conftest import client_for
from .test_api import HABIT, today
from .test_bot import USER_ID, FakeBot, local, setup, tick


@contextlib.asynccontextmanager
async def listening(on_change):
    task = asyncio.create_task(listen(asyncpg_dsn(settings.database_url), on_change))
    await asyncio.sleep(0.5)  # LISTEN успевает подписаться
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


async def wait_for(predicate, timeout: float = 3) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.05)


async def test_api_changes_are_notified_after_commit():
    got: list[int | None] = []
    async with listening(got.append), client_for(5005) as c:
        await c.get("/api/me")
        assert got == []  # чтение и вход ничего не меняют — иначе приложение перечитывало бы по кругу
        habit = (await c.post("/api/habits", json=HABIT)).json()
        await wait_for(lambda: got == [5005])
        assert (await c.put(f"/api/habits/{habit['id']}/marks/{today()}", json={"kind": "full"})).status_code == 200
        await wait_for(lambda: got == [5005, 5005])
        # Отклонённый запрос откатывается — уведомления нет.
        assert (await c.put(f"/api/habits/{habit['id']}/marks/2000-01-01", json={"kind": "full"})).status_code == 422
        assert (await c.delete(f"/api/habits/{habit['id']}/marks/{today()}")).status_code == 204
        await wait_for(lambda: got == [5005, 5005, 5005])


async def test_event_stream_sends_changed_to_own_user_only():
    stream = event_stream(42, ping=0.2)
    assert await anext(stream) == ": connected\n\n"
    nxt = asyncio.ensure_future(anext(stream))
    await asyncio.sleep(0)
    broker.publish(43)
    assert await nxt == ": ping\n\n"  # чужое изменение не пришло
    nxt = asyncio.ensure_future(anext(stream))
    await asyncio.sleep(0)
    broker.publish(42)
    broker.publish(42)  # два изменения подряд — одно событие
    assert await nxt == "event: changed\ndata: {}\n\n"
    assert await asyncio.wait_for(anext(stream), 1) == ": ping\n\n"
    await stream.aclose()
    assert 42 not in broker._queues


async def test_broker_after_reconnect_notifies_everyone():
    b = Broker()
    with b.subscribe(1) as q1, b.subscribe(2) as q2:
        b.publish(None)
        assert not q1.empty() and not q2.empty()


async def test_bot_message_follows_marks_from_app():
    user, habit = await setup()
    bot = FakeBot()
    assert await tick(bot, local(7, 46)) == 1

    async with SessionLocal() as session:
        await marks.put_mark(session, user, habit.id, user_today(user), "mini")
    async with SessionLocal() as session:
        assert await refresh_messages(session, bot, USER_ID) == 1
    message_id, text, keyboard = bot.edited[-1]
    assert message_id == 101
    assert "Две минуты засчитаны." in text
    assert keyboard.inline_keyboard[0][0].text == "Отменить"

    async with SessionLocal() as session:
        await marks.delete_mark(session, await session.get(User, USER_ID), habit.id, user_today(user))
    async with SessionLocal() as session:
        await refresh_messages(session, bot, USER_ID)
    _, text, keyboard = bot.edited[-1]
    assert "самое время" in text
    assert keyboard.inline_keyboard[0][0].text == "Сделал"


async def test_evening_message_stays_evening_after_undo():
    user, habit = await setup()
    bot = FakeBot()
    assert await tick(bot, local(21, 5)) == 1
    async with SessionLocal() as session:
        await marks.put_mark(session, user, habit.id, user_today(user), "full")
        await marks.delete_mark(session, user, habit.id, user_today(user))
    async with SessionLocal() as session:
        await refresh_messages(session, bot, USER_ID)
    _, text, keyboard = bot.edited[-1]
    assert "Сегодня ещё без капли" in text
    assert len(keyboard.inline_keyboard) == 1  # у вечернего только кнопки отметки


async def test_no_reminder_today_nothing_to_edit():
    user, habit = await setup()
    bot = FakeBot()
    async with SessionLocal() as session:
        await marks.put_mark(session, user, habit.id, user_today(user), "full")
    async with SessionLocal() as session:
        assert await refresh_messages(session, bot, USER_ID) == 0
    assert bot.edited == []


async def test_mark_in_app_edits_bot_message_end_to_end():
    """Цепочка целиком: отметка через API → NOTIFY → бот перерисовал сообщение."""
    _, habit = await setup()
    bot = FakeBot()
    assert await tick(bot, local(7, 46)) == 1
    async with listening(MessageSync(bot, SessionLocal).changed), client_for(USER_ID) as c:
        r = await c.put(f"/api/habits/{habit.id}/marks/{today()}", json={"kind": "full"})
        assert r.status_code == 200
        await wait_for(lambda: any("Сделал полностью" in t for _, t, _ in bot.edited))
