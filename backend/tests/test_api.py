import datetime as dt
from zoneinfo import ZoneInfo

from httpx import AsyncClient

from .conftest import client_for

HABIT = {
    "identity": "читает",
    "full": "читаю 30 минут",
    "mini": "прочитать одну страницу",
    "anchor": "налью утренний кофе",
}


def today(tz: str = "Europe/Moscow") -> str:
    return dt.datetime.now(ZoneInfo(tz)).date().isoformat()


async def create(client: AsyncClient, **extra) -> dict:
    r = await client.post("/api/habits", json={**HABIT, **extra})
    assert r.status_code == 201, r.text
    return r.json()


async def test_requires_auth():
    from httpx import ASGITransport

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
        assert (await anon.get("/api/habits")).status_code == 401
        r = await anon.get("/api/habits", headers={"Authorization": "tma auth_date=1&hash=00"})
        assert r.status_code == 401


async def test_me_creates_user_with_timezone():
    async with client_for(7, timezone="Asia/Vladivostok") as c:
        r = await c.get("/api/me")
    assert r.status_code == 200
    assert r.json()["timezone"] == "Asia/Vladivostok"
    assert r.json()["today"] == today("Asia/Vladivostok")


async def test_create_and_list(client: AsyncClient):
    habit = await create(client, reward="любимый чай")
    assert habit["identity"] == "читает"
    assert habit["status"] == "active"
    assert habit["createdAt"] == today()
    assert habit["marks"] == [] and habit["pauses"] == [] and habit["reminder"] is None

    r = await client.get("/api/habits")
    assert [h["id"] for h in r.json()] == [habit["id"]]


async def test_validation(client: AsyncClient):
    r = await client.post("/api/habits", json={**HABIT, "identity": "   "})
    assert r.status_code == 422


async def test_mark_is_idempotent_and_undo(client: AsyncClient):
    habit = await create(client)
    url = f"/api/habits/{habit['id']}/marks/{today()}"

    assert (await client.put(url, json={"kind": "full"})).status_code == 200
    r = await client.put(url, json={"kind": "mini"})
    assert r.status_code == 200 and r.json()["kind"] == "mini"

    marks = (await client.get("/api/habits")).json()[0]["marks"]
    assert len(marks) == 1 and marks[0]["kind"] == "mini"

    assert (await client.delete(url)).status_code == 204
    assert (await client.get("/api/habits")).json()[0]["marks"] == []


async def test_mark_date_window(client: AsyncClient):
    habit = await create(client)
    old = (dt.date.fromisoformat(today()) - dt.timedelta(days=3)).isoformat()
    r = await client.put(f"/api/habits/{habit['id']}/marks/{old}", json={"kind": "full"})
    assert r.status_code == 422


async def test_pause_and_resume(client: AsyncClient):
    habit = await create(client)
    r = await client.post(f"/api/habits/{habit['id']}/pause")
    assert r.json()["status"] == "paused"
    assert r.json()["pauses"] == [{"start": today(), "end": None}]

    r = await client.put(f"/api/habits/{habit['id']}/marks/{today()}", json={"kind": "full"})
    assert r.status_code == 409

    r = await client.post(f"/api/habits/{habit['id']}/resume")
    assert r.json()["status"] == "active"
    assert r.json()["pauses"] == [{"start": today(), "end": today()}]


async def test_patch_and_delete(client: AsyncClient):
    habit = await create(client, reward="чай")
    r = await client.patch(f"/api/habits/{habit['id']}", json={"full": "читаю 20 минут", "reward": None})
    assert r.json()["full"] == "читаю 20 минут" and r.json()["reward"] is None

    assert (await client.patch(f"/api/habits/{habit['id']}", json={"mini": None})).status_code == 422

    assert (await client.delete(f"/api/habits/{habit['id']}")).status_code == 204
    assert (await client.get("/api/habits")).json() == []


async def test_reminder(client: AsyncClient):
    habit = await create(client)
    url = f"/api/habits/{habit['id']}/reminder"
    assert (await client.get(url)).json() is None

    r = await client.put(url, json={"time": "07:45", "days": [5, 1, 2, 2], "evening": True})
    assert r.json() == {"time": "07:45:00", "days": [1, 2, 5], "evening": True}

    habits = (await client.get("/api/habits")).json()
    assert habits[0]["reminder"]["days"] == [1, 2, 5]


async def test_cannot_touch_other_users_habit(client: AsyncClient):
    habit = await create(client)
    async with client_for(2002) as other:
        assert (await other.get("/api/habits")).json() == []
        r = await other.put(f"/api/habits/{habit['id']}/marks/{today()}", json={"kind": "full"})
        assert r.status_code == 404
        assert (await other.delete(f"/api/habits/{habit['id']}")).status_code == 404
