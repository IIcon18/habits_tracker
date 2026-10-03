# Капля — бэкенд

FastAPI + PostgreSQL. Проверяет подпись Telegram `initData`, хранит привычки, отметки, паузы и напоминания.

## Запуск

```bash
cp .env.example .env          # из корня проекта; впиши BOT_TOKEN
docker compose up -d          # Postgres на :5433, API на :8001 (миграции применяются сами)
curl localhost:8001/health
```

Без Docker (нужен запущенный `db` из compose):

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8001
```

Тесты (база `kaplya_test` создаётся контейнером `db` автоматически):

```bash
.venv/bin/pytest
```

Новая миграция после изменения `app/models.py`: `.venv/bin/alembic revision --autogenerate -m "что изменилось"`.

## Разработка без Telegram

В `.env`: `DEBUG=1`, `DEV_USER_ID=1` — запросы без `initData` идут от этого пользователя.
Фронтенд в этом режиме: `cd frontend && VITE_USE_API=1 npm run dev` (Vite проксирует `/api` на `:8001`).

## Открыть в Telegram

Mini App работает только по HTTPS:

1. `cd frontend && npm run dev`, затем туннель: `cloudflared tunnel --url http://localhost:5173` (или `ngrok http 5173`).
2. В @BotFather: `/mybots` → бот → Bot Settings → Menu Button → URL туннеля.
3. `BOT_TOKEN` в `.env` должен быть от этого же бота, иначе подпись не сойдётся (401).

## API (`/api`, JSON в camelCase)

| Метод | Путь | Что делает |
| --- | --- | --- |
| GET | `/me` | пользователь, его часовой пояс и «сегодня» |
| GET | `/habits` | привычки с отметками, паузами и напоминанием |
| POST | `/habits` | создать (`identity`, `full`, `mini`, `anchor`, `reward?`) |
| PATCH | `/habits/{id}` | изменить поля |
| DELETE | `/habits/{id}` | удалить |
| POST | `/habits/{id}/pause`, `/resume` | пауза / вернуть |
| PUT | `/habits/{id}/marks/{date}` | отметка `{kind: full\|mini, at?}`, идемпотентно; сегодня или вчера |
| DELETE | `/habits/{id}/marks/{date}` | отменить, только сегодня |
| GET / PUT | `/habits/{id}/reminder` | напоминание `{time, days[1..7], evening}` |

Заголовки: `Authorization: tma <initData>`, `X-Timezone: <IANA>`.
Логика серии — `app/stats.py`, зеркало `frontend/src/lib/stats.ts`: меняешь одно — меняй и другое.
