import { addDays, type ISODate } from './date';
import type { Habit, Mark, MarkKind } from './types';

/** Состояния ячейки ряда дней — см. design/04-components.md, DayCell. */
export type DayState = 'full' | 'mini' | 'miss' | 'miss2' | 'today-empty' | 'before';

export type MissState = 'none' | 'one' | 'two';

export interface HabitStats {
  /** 14 дней, последний — сегодня. */
  days: DayState[];
  votes: number;
  streak: number;
  todayMark?: Mark;
  /** «вчера пропуск» / «два пропуска» — только пока сегодня не отмечено. */
  missState: MissState;
}

export const ROW_LENGTH = 14;

/**
 * Правила из design/01-product.md:
 * голоса — все отметки; один пропуск не обнуляет серию, но и не добавляет к ней;
 * два пропуска подряд обнуляют серию; дни на паузе не считаются пропусками.
 * Та же логика на сервере — backend/app/stats.py; меняешь здесь — поменяй и там.
 */
export function computeStats(habit: Habit, marks: Mark[], today: ISODate): HabitStats {
  const byDate = new Map<ISODate, MarkKind>();
  for (const m of marks) if (m.habitId === habit.id) byDate.set(m.date, m.kind);

  const onPause = (d: ISODate) => habit.pauses.some((p) => p.start <= d && (p.end === null || d < p.end));
  const isTracked = (d: ISODate) => d >= habit.createdAt && !onPause(d);
  const isMiss = (d: ISODate) => d < today && isTracked(d) && !byDate.has(d);

  let streak = 0;
  let missRun = 0;
  for (let d = habit.createdAt; d < today; d = addDays(d, 1)) {
    if (!isTracked(d)) continue;
    if (byDate.has(d)) {
      streak += 1;
      missRun = 0;
    } else if (++missRun >= 2) {
      streak = 0;
    }
  }

  const todayKind = byDate.get(today);
  if (todayKind) streak += 1;

  const yesterday = addDays(today, -1);
  const dayBefore = addDays(today, -2);
  let missState: MissState = 'none';
  if (!todayKind && isMiss(yesterday)) missState = isMiss(dayBefore) ? 'two' : 'one';

  const days: DayState[] = [];
  for (let i = ROW_LENGTH - 1; i >= 0; i--) {
    const d = addDays(today, -i);
    const kind = byDate.get(d);
    if (kind) days.push(kind);
    else if (d === today) days.push('today-empty');
    else if (!isTracked(d)) days.push('before');
    else if (missState === 'two' && (d === yesterday || d === dayBefore)) days.push('miss2');
    else days.push('miss');
  }

  return {
    days,
    votes: byDate.size,
    streak,
    todayMark: marks.find((m) => m.habitId === habit.id && m.date === today),
    missState,
  };
}
