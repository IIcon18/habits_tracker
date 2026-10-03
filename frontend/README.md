# Капля — фронтенд (Telegram Mini App)

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # проверка типов + сборка в dist/
```

Вне Telegram приложение открывается в обычном браузере (лучше в режиме устройства, ширина 390px).
Параметры для проверки макетов:

- `?theme=light` — светлая тема (в Telegram тема берётся из `colorScheme`);
- `?demo=paused` — экран 1.4, `?demo=two` — два пропуска подряд, `?demo=new` — новая привычка.

Маршруты (HashRouter): `#/today` — «Сегодня», `#/new/1…4` — мастер создания.

Системные кнопки Telegram объявляются хуками `useMainButton` / `useSecondaryButton` / `useBackButton`
(`src/lib/tgButtons.tsx`). Вне Telegram MainButton и SecondaryButton имитирует нижняя панель —
только для разработки, внутри Telegram её нет.

Данные: внутри Telegram — API бэкенда (`src/lib/api.ts`, см. `backend/README.md`).
В браузере по умолчанию — демо-данные (`src/lib/demo.ts`); с бэкендом — `VITE_USE_API=1 npm run dev`
(бэкенд с `DEBUG=1` и `DEV_USER_ID`). Подсказка ИИ пока заглушка (`src/lib/ai.ts`).
