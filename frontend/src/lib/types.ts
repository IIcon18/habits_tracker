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
  reward?: string;
  status: 'active' | 'paused';
  pausedAt?: ISODate;
  createdAt: ISODate;
}

export interface Mark {
  habitId: string;
  date: ISODate;
  kind: MarkKind;
  /** Время отметки, ms. */
  at: number;
}
