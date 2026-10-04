# Деплой

Прод: https://wavestodream.ru, сервер `89.208.106.122` (DNS в reg.ru: A-записи `@` и `www`).

На сервере в Docker (`docker-compose.prod.yml`): `db` (Postgres), `api` (FastAPI), `bot` (aiogram,
polling) и `web` — Caddy. Caddy раздаёт собранный фронтенд, проксирует `/api` в `api:8000`
и сам выпускает сертификат Let's Encrypt. Наружу открыты только 80 и 443; `www` редиректит на основной домен.

## Выкатить

```bash
./deploy.sh
```

Скрипт заходит под `root` (пароль спросит один раз), копирует текущую папку проекта без файлов
из `.gitignore` в `/opt/kaplya`, пересобирает контейнеры и ждёт, пока `https://wavestodream.ru/api/me`
ответит 401 (API живой и требует подпись Telegram). Миграции применяются при старте `api`.

Первый запуск сам ставит Docker и создаёт `/opt/kaplya/.env`: спросит `BOT_TOKEN`,
пароль Postgres сгенерирует. Дальше `.env` на сервере не трогается — правь его по SSH.

Другой сервер или домен: `SERVER=root@1.2.3.4 DOMAIN=example.ru ./deploy.sh`.

Бот с одним токеном может работать только в одном месте: если он запущен локально
(`docker compose up`), останови его — `docker compose stop bot`.

## На сервере

```bash
ssh root@89.208.106.122
cd /opt/kaplya
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api bot web
```

Бэкап базы:

```bash
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U kaplya kaplya | gzip > backup-$(date +%F).sql.gz
```
