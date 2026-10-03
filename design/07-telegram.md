# 07 · Интеграция с Telegram

Документация: https://core.telegram.org/bots/webapps. Перед использованием метода проверь `Telegram.WebApp.isVersionAtLeast(...)` и сверься с документацией — названия ниже по состоянию на 2026 год.

## Запуск

```js
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
applyTheme();
tg.onEvent('themeChanged', applyTheme);

function applyTheme() {
  document.documentElement.dataset.theme = tg.colorScheme === 'light' ? 'light' : 'dark';
  const ground = getComputedStyle(document.documentElement).getPropertyValue('--ground').trim();
  tg.setHeaderColor(ground);
  tg.setBackgroundColor(ground);
  tg.setBottomBarColor?.(ground);
}
```

- Цвета приложения — свои (из `tokens.css`), а не `themeParams`. От Telegram берём только `colorScheme` (светлая/тёмная).
- Безопасные зоны — см. `03-layout.md`.

## Системные кнопки

| Кнопка | Где | Настройка |
| --- | --- | --- |
| `MainButton` | главное действие экрана (таблица в `05-screens.md`) | `setParams({ text, color: --accent, text_color: --on-accent, is_active, is_visible })`. Неактивная — `color: --surface-sunk`, `text_color: --ink-muted`. |
| `SecondaryButton` | «Без награды» (5.4), «В историю» (7.2) | `color: --accent-soft`, `text_color: --on-accent-soft`, `position: 'left'` |
| `BackButton` | все экраны, кроме «Сегодня», первого шага знакомства и пустого состояния | показывать при входе на экран, скрывать при выходе |

Свою кнопку «Назад» и свою нижнюю главную кнопку не рисуем — на макетах они нарисованы только для наглядности.

## Диалоги

- **Удаление** (6.4) — `tg.showPopup({ title: 'Удалить привычку?', message: '«Я человек, который читает» и 23 голоса пропадут насовсем. Если нужен перерыв, лучше поставить на паузу.', buttons: [{id:'pause', type:'default', text:'Поставить на паузу'}, {id:'delete', type:'destructive', text:'Удалить'}, {type:'cancel'}] })`.
- **Разрешение писать** — `tg.requestWriteAccess(cb)`. Вызывать при первом включении напоминания. Если отказ — экран 8.4.

## Хранилище и данные

- `initData` отправляй на сервер для проверки подписи; `initDataUnsafe.user` — только для отображения.
- Флаг «знакомство показано» и черновик создания — `tg.CloudStorage`.
- Отметки без сети — в локальной очереди (IndexedDB), отправка при восстановлении сети (экран 9.2).

## Шеринг

- В чат — `tg.shareMessage(preparedMessageId)` (сообщение готовит бот через `savePreparedInlineMessage`), картинка — ShareCard, кнопка «Попробовать Каплю» со ссылкой на Mini App.
- В историю — `tg.shareToStory(imageUrl, { text, widget_link: { url, name: 'Капля' } })`.

## Отклик

`tg.HapticFeedback.impactOccurred('light')` на нажатие отметки, `notificationOccurred('success')` после сохранения, `notificationOccurred('error')` при ошибке (9.3), `selectionChanged()` на чипах и барабанах.
