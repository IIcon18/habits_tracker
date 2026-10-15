"""Поток событий для открытого Mini App: «данные изменились — перечитай».

Отметка из бота, из другого устройства или окна сразу видна в приложении без перезапуска.
Сами данные по потоку не идут: приложение перечитывает их обычным GET /api/habits.
"""

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser

router = APIRouter(tags=["events"])

# Комментарий в потоке раз в 25 с: прокси и мобильные сети не закрывают соединение без трафика.
PING_SECONDS = 25


class Broker:
    """Раздаёт уведомления из LISTEN (app.core.notify) открытым потокам этого процесса."""

    def __init__(self) -> None:
        self._queues: defaultdict[int, set[asyncio.Queue[None]]] = defaultdict(set)

    def publish(self, user_id: int | None) -> None:
        """None — уведомления могли потеряться: сообщаем всем."""
        targets = self._queues.get(user_id, ()) if user_id is not None else [q for qs in self._queues.values() for q in qs]
        for queue in targets:
            # Очередь на одно место: несколько изменений подряд — одно перечитывание.
            if queue.empty():
                queue.put_nowait(None)

    @contextmanager
    def subscribe(self, user_id: int) -> Iterator[asyncio.Queue[None]]:
        queue: asyncio.Queue[None] = asyncio.Queue(maxsize=1)
        self._queues[user_id].add(queue)
        try:
            yield queue
        finally:
            self._queues[user_id].discard(queue)
            if not self._queues[user_id]:
                del self._queues[user_id]


broker = Broker()


async def event_stream(user_id: int, ping: float = PING_SECONDS) -> AsyncIterator[str]:
    with broker.subscribe(user_id) as queue:
        # Первая строка сразу: клиент понимает, что подключился.
        yield ": connected\n\n"
        while True:
            try:
                await asyncio.wait_for(queue.get(), ping)
            except TimeoutError:
                yield ": ping\n\n"
            else:
                yield "event: changed\ndata: {}\n\n"


@router.get("/events")
async def events(user: CurrentUser) -> StreamingResponse:
    return StreamingResponse(
        event_stream(user.id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
