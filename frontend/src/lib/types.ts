import type { ISODate } from './date';

export type MarkKind = 'full' | 'mini';

export interface Habit {
  id: string;
  /** Окончание идентичности: «читает» → «Я человек, который читает». */
  identity: string;
  full: string;
  mini: string;
  /** Якорь без префикса: «налью утренний кофе» → «После того как налью утренний кофе». */
  anchor: string;
  reward?: string | null;
  status: 'active' | 'paused';
  /** Интервалы паузы [start, end); end = null — пауза идёт. Дни на паузе не пропуски. */
  pauses: Pause[];
  createdAt: ISODate;
  reminder?: Reminder | null;
}

export interface Pause {
  start: ISODate;
  end: ISODate | null;
}

export interface Reminder {
  /** «07:45» */
  time: string;
  /** 1 (пн) … 7 (вс) */
  days: number[];
  evening: boolean;
}

export interface Mark {
  habitId: string;
  date: ISODate;
  kind: MarkKind;
  /** Время отметки, ms. */
  at: number;
}
