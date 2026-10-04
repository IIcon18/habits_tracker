#!/usr/bin/env bash
# Деплой на сервер: ./deploy.sh
# Заходит по SSH под root (пароль спрашивает один раз), при первом запуске ставит Docker
# и создаёт .env на сервере, затем копирует код и пересобирает контейнеры.
# Копируется текущее состояние папки (включая незакоммиченное), кроме файлов из .gitignore.
set -euo pipefail

SERVER=${SERVER:-root@89.208.106.122}
DOMAIN=${DOMAIN:-wavestodream.ru}
APP_DIR=/opt/kaplya
COMPOSE="docker compose -f docker-compose.prod.yml"

cd "$(dirname "$0")"

# Одно SSH-соединение на весь скрипт — пароль вводится один раз.
SOCKET=$(mktemp -u /tmp/kaplya-ssh.XXXXXX)
echo "→ Подключаюсь к $SERVER"
ssh -o ControlMaster=yes -o ControlPath="$SOCKET" -o ControlPersist=15m -fN "$SERVER"
trap 'ssh -o ControlPath="$SOCKET" -O exit "$SERVER" 2>/dev/null || true' EXIT
remote() { ssh -o ControlPath="$SOCKET" "$SERVER" "$@"; }

echo "→ Docker"
remote 'command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh'
# Если включён ufw — открываем порты для Caddy.
remote 'if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null; ufw allow 443/udp >/dev/null
fi'

if ! remote "test -f $APP_DIR/.env"; then
  echo "→ На сервере нет $APP_DIR/.env — создаю"
  read -rsp "BOT_TOKEN (ввод скрыт): " BOT_TOKEN; echo
  remote "mkdir -p $APP_DIR && umask 077 && cat > $APP_DIR/.env" <<EOF
BOT_TOKEN=$BOT_TOKEN
DOMAIN=$DOMAIN
POSTGRES_USER=kaplya
POSTGRES_PASSWORD=$(openssl rand -hex 24)
POSTGRES_DB=kaplya
EOF
fi

echo "→ Копирую код ($(git rev-parse --short HEAD)$(git diff --quiet HEAD || echo ', есть незакоммиченные изменения'))"
# .env на сервере не трогаем, всё остальное заменяем — удалённые файлы не останутся.
remote "find $APP_DIR -mindepth 1 -maxdepth 1 ! -name .env -exec rm -rf {} +"
git ls-files -z --cached --others --exclude-standard -- backend frontend docker-compose.prod.yml \
  | while IFS= read -r -d '' f; do [ -e "$f" ] && printf '%s\0' "$f"; done \
  | COPYFILE_DISABLE=1 tar --null -T - --no-xattrs --no-mac-metadata -czf - \
  | remote "tar -xzf - -C $APP_DIR"

echo "→ Сборка и запуск"
remote "cd $APP_DIR && $COMPOSE up -d --build --remove-orphans && docker image prune -f >/dev/null"

echo "→ Жду https://$DOMAIN"
for _ in $(seq 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "https://$DOMAIN/api/me" || true)
  # 401 — API отвечает и требует подпись Telegram, то есть всё поднялось.
  if [ "$code" = 401 ]; then
    remote "cd $APP_DIR && $COMPOSE ps"
    echo "✓ Готово: https://$DOMAIN"
    exit 0
  fi
  sleep 4
done

echo "✗ https://$DOMAIN не ответил. Логи: ssh $SERVER 'cd $APP_DIR && $COMPOSE logs --tail 50'"
remote "cd $APP_DIR && $COMPOSE ps && $COMPOSE logs --tail 30 web api"
exit 1
