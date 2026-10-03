# Капля — бэкенд

FastAPI + PostgreSQL. Проверяет подпись Telegram `initData`, хранит привычки, отметки, паузы и напоминания.

## Структура

```
app/
  main.py        приложение FastAPI, перевод доменных ошибок в HTTP-коды
  core/          config (настройки из .env), database (engine, сессия, Base),
                 security (проверка подписи initData), exceptions (доменные ошибки)
  models/        таблицы SQLAlchemy — по файлу на сущность
  schemas/       Pydantic-схемы запросов и ответов (JSON в camelCase)
  services/      бизнес-логика: users, habits, marks, reminders, stats (серия и пропуски).
                 Не знает про HTTP — эти же функции будет вызывать бот
  api/           deps (сессия, текущий пользователь), routes/ — тонкие роуты, router.py
  bot/           Telegram-бот (aiogram): texts — тексты из design/09-bot.md, keyboards, handlers
                 (/start, кнопки «Сделал» / «2 минуты» / «Отменить»), scheduler — напоминания
alembic/         миграции
tests/
```

## Запуск

```bash
cp .env.example .env          # из корня проекта; впиши BOT_TOKEN
docker compose up -d          # Postgres на :5433, API на :8001 (миграции применяются сами), бот
curl localhost:8001/health
```

Без Docker (нужен запущенный `db` из compose):

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8001
```

Тесты (нужен запущенный `db`; тестовую базу `kaplya_test` тесты создают сами, если её нет):

```bash
.venv/bin/pytest
```

Новая миграция после изменения `app/models/`: `.venv/bin/alembic revision --autogenerate -m "что изменилось"`.

## Разработка без Telegram

В `.env`: `DEBUG=1`, `DEV_USER_ID=1` — запросы без `initData` идут от этого пользователя.
Фронтенд в этом режиме: `cd frontend && VITE_USE_API=1 npm run dev` (Vite проксирует `/api` на `:8001`).

## Открыть в Telegram

Mini App работает только по HTTPS:

1. `cd frontend && npm run dev`, затем туннель: `cloudflared tunnel --url http://localhost:5173` (или `ngrok http 5173`).
2. Адрес туннеля — в `.env` как `WEBAPP_URL`, затем `docker compose up -d bot` (перезапуск подхватит адрес).
   Бот сам поставит кнопку меню «Капля» — в @BotFather ничего настраивать не нужно.
3. `BOT_TOKEN` в `.env` должен быть от этого же бота, иначе подпись не сойдётся (401).
4. Напиши боту `/start` — без этого Telegram не разрешит ему присылать напоминания.

## Бот

- Работает через polling: сам забирает обновления у Telegram, входящий адрес не нужен.
- Раз в минуту проверяет напоминания по часовому поясу каждого пользователя: утреннее — во время
  из настроек, вечернее — в 21:00, если за день нет отметки; после двух пропусков — сообщение
  «Два дня без капли» с кнопками в обратном порядке. Дата отправки хранится в `reminders.last_*_on`:
  дважды не придёт, а если бот был выключен, догонит в течение часа.
- Кнопки «Сделал» / «2 минуты» / «Отменить» вызывают те же сервисы, что и API.
- Если Telegram отвечает 403 (человек не нажимал /start или заблокировал бота) — `users.allows_write = false`,
  напоминания ему не шлются до следующего /start.
- Логи: `docker compose logs -f bot`.

Пока в приложении нет экрана напоминания (6.1), напоминание можно включить запросом:

```bash
curl -X PUT localhost:8001/api/habits/<id>/reminder -H 'Content-Type: application/json' \
  -d '{"time": "07:45", "days": [1,2,3,4,5,6,7], "evening": true}'
```

(с `DEBUG=1` и `DEV_USER_ID` = твоему Telegram id; id привычки — из `curl localhost:8001/api/habits`).

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
Логика серии — `app/services/stats.py`, зеркало `frontend/src/lib/stats.ts`: меняешь одно — меняй и другое.
