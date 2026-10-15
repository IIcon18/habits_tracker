"""Уведомления об изменениях данных пользователя между процессами — через Postgres LISTEN/NOTIFY.

Сервисы в той же транзакции, что и изменение, вызывают notify_changed: Postgres доставит
уведомление только после коммита. API пересылает его открытому Mini App (поток /api/events),
бот — перерисовывает своё сообщение в чате. Так отметка из чата сразу видна в приложении, и наоборот.
"""

import asyncio
import logging
from collections.abc import Callable

import asyncpg
from sqlalchemy import func, make_url, select
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

CHANNEL = "kaplya_changes"
# Как часто проверять, что соединение живо: обрыв сети без закрытия соединения иначе не заметить.
HEALTH_CHECK = 30
RETRY = 2


async def notify_changed(session: AsyncSession, user_id: int) -> None:
    """Отметить, что у пользователя изменились привычки или отметки. Уйдёт при коммите сессии."""
    await session.execute(select(func.pg_notify(CHANNEL, str(user_id))))


def asyncpg_dsn(database_url: str) -> str:
    """postgresql+asyncpg://… → postgresql://… для прямого подключения asyncpg."""
    return make_url(database_url).set(drivername="postgresql").render_as_string(hide_password=False)


async def listen(dsn: str, on_change: Callable[[int | None], None]) -> None:
    """Слушает CHANNEL, пока задачу не отменят; при обрыве переподключается.

    on_change(user_id) — изменились данные этого пользователя. on_change(None) — соединение
    восстановлено после обрыва и уведомления могли потеряться: изменилось что угодно.
    """
    first = True
    while True:
        try:
            conn = await asyncpg.connect(dsn)
        except (OSError, asyncpg.PostgresError):
            log.warning("нет соединения с базой для LISTEN, повтор через %s с", RETRY)
            await asyncio.sleep(RETRY)
            continue
        try:
            lost = asyncio.Event()
            conn.add_termination_listener(lambda _: lost.set())
            await conn.add_listener(CHANNEL, lambda _c, _pid, _ch, payload: on_change(int(payload)))
            if not first:
                on_change(None)
            first = False
            while not lost.is_set():
                try:
                    await asyncio.wait_for(lost.wait(), HEALTH_CHECK)
                except TimeoutError:
                    await conn.fetchval("SELECT 1", timeout=5)
        except (OSError, TimeoutError, asyncpg.PostgresError, asyncpg.InterfaceError):
            log.warning("соединение LISTEN потеряно, переподключаюсь")
        finally:
            if not conn.is_closed():
                conn.terminate()
        await asyncio.sleep(RETRY)
