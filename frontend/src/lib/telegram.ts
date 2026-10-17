/**
 * Интеграция с Telegram Web App — design/07-telegram.md.
 * Вне Telegram (обычный браузер при разработке) все вызовы безопасно ничего не делают,
 * а тема берётся из ?theme=light|dark, по умолчанию — тёмная.
 */

import type { WebApp } from 'telegram-web-app';

export const tg: WebApp | undefined = window.Telegram?.WebApp;

/** true, только если приложение реально открыто внутри Telegram. */
export const insideTelegram = Boolean(tg?.initData);

function safe(fn: () => void) {
  try {
    fn();
  } catch {
    /* метод не поддерживается этой версией клиента */
  }
}

function resolveScheme(): 'light' | 'dark' {
  if (insideTelegram) return tg!.colorScheme === 'light' ? 'light' : 'dark';
  const forced = new URLSearchParams(location.search).get('theme');
  return forced === 'light' ? 'light' : 'dark';
}

function applyTheme() {
  const root = document.documentElement;
  root.dataset.theme = resolveScheme();
  if (!insideTelegram) return;
  const ground = getComputedStyle(root).getPropertyValue('--ground').trim();
  safe(() => tg!.setHeaderColor(ground));
  safe(() => tg!.setBackgroundColor(ground));
  if (tg!.isVersionAtLeast('7.10')) safe(() => tg!.setBottomBarColor(ground));
}

export function initTelegram() {
  applyTheme();
  if (!insideTelegram) return;
  tg!.ready();
  tg!.expand();
  tg!.onEvent('themeChanged', applyTheme);
}

/**
 * Разрешение боту писать (design/07-telegram.md). Если уже разрешено, Telegram отвечает сразу, без окна.
 * Вне Telegram — для проверки экрана 8.4 в браузере: ?write=deny означает отказ.
 */
export function requestWriteAccess(): Promise<boolean> {
  if (!insideTelegram) return Promise.resolve(new URLSearchParams(location.search).get('write') !== 'deny');
  // Старый клиент не умеет спрашивать — считаем, что можно: бот сам узнает об отказе при отправке.
  if (!tg!.isVersionAtLeast('6.9')) return Promise.resolve(true);
  return new Promise((resolve) => {
    try {
      tg!.requestWriteAccess((allowed) => resolve(allowed));
    } catch {
      resolve(true);
    }
  });
}

export const haptic = {
  /** На нажатие отметки. */
  tap: () => insideTelegram && safe(() => tg!.HapticFeedback.impactOccurred('light')),
  success: () => insideTelegram && safe(() => tg!.HapticFeedback.notificationOccurred('success')),
  error: () => insideTelegram && safe(() => tg!.HapticFeedback.notificationOccurred('error')),
  selection: () => insideTelegram && safe(() => tg!.HapticFeedback.selectionChanged()),
};
