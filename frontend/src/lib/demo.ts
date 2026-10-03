/**
 * Демо-данные, пока нет бэкенда. Сценарий выбирается параметром ?demo=…:
 *   (по умолчанию) — экран 1.1, `paused` — 1.4, `two` — два пропуска, `new` — новая привычка.
 */
import { addDays, todayISO } from './date';
import type { Habit, Mark } from './types';

/** Паттерн по дням с начала привычки до вчера: d — сделал, m — 2 минуты, x — пропуск. */
function marksFrom(habitId: string, createdAt: string, pattern: string): Mark[] {
  const marks: Mark[] = [];
  [...pattern].forEach((ch, i) => {
    if (ch === 'x') return;
    const date = addDays(createdAt, i);
    const at = new Date(`${date}T07:42:00`).getTime();
    marks.push({ habitId, date, kind: ch === 'd' ? 'full' : 'mini', at });
  });
  return marks;
}

function habit(id: string, fields: Omit<Habit, 'id' | 'status' | 'pauses'>): Habit {
  return { id, status: 'active', pauses: [], ...fields };
}

export function loadDemo(): { habits: Habit[]; marks: Mark[] } {
  const today = todayISO();
  const scenario = new URLSearchParams(location.search).get('demo');

  const readStart = addDays(today, -29);
  const readPattern = 'dmdxddmddxxddddmdxddmdxddddddd'.slice(0, 29);
  const read = habit('read', {
    identity: 'читает',
    anchor: 'налью утренний кофе',
    full: 'читаю 30 минут',
    mini: 'одна страница',
    createdAt: readStart,
  });

  const moveStart = addDays(today, -20);
  const movePattern = scenario === 'two' ? 'dxmdddxdmdddmxdmddxx' : 'dxmdddxdmdddmxdmdddx';
  const move = habit('move', {
    identity: 'двигается',
    anchor: 'закрою ноутбук',
    full: 'гуляю 20 минут',
    mini: 'надеть кроссовки и выйти за дверь',
    createdAt: moveStart,
  });

  const readMarks = [
    ...marksFrom('read', readStart, readPattern),
    { habitId: 'read', date: today, kind: 'full' as const, at: new Date(`${today}T07:42:00`).getTime() },
  ];
  const moveMarks = marksFrom('move', moveStart, movePattern);

  if (scenario === 'paused') {
    const pausedAt = addDays(today, -4);
    return {
      habits: [read, { ...move, status: 'paused', pauses: [{ start: pausedAt, end: null }] }],
      marks: [...readMarks, ...moveMarks.filter((m) => m.date < pausedAt)],
    };
  }

  if (scenario === 'new') {
    const write = habit('write', {
      identity: 'пишет',
      anchor: 'сяду за стол вечером',
      full: 'пишу 15 минут',
      mini: 'одно предложение в заметки',
      createdAt: today,
    });
    return { habits: [read, write], marks: readMarks };
  }

  return { habits: [read, move], marks: [...readMarks, ...moveMarks] };
}
