/** Дата в формате YYYY-MM-DD в локальном часовом поясе пользователя. */
export type ISODate = string;

const pad = (n: number) => String(n).padStart(2, '0');

export function toISODate(d: Date): ISODate {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function fromISODate(s: ISODate): Date {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, m - 1, d);
}

export function addDays(s: ISODate, days: number): ISODate {
  const d = fromISODate(s);
  d.setDate(d.getDate() + days);
  return toISODate(d);
}

export const todayISO = () => toISODate(new Date());

/** «Пятница» */
export function weekdayLabel(s: ISODate): string {
  const w = fromISODate(s).toLocaleDateString('ru-RU', { weekday: 'long' });
  return w.charAt(0).toUpperCase() + w.slice(1);
}

/** «2 октября» */
export function dayMonthLabel(s: ISODate): string {
  return fromISODate(s).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
}

/** «7:42» */
export function timeLabel(at: number): string {
  const d = new Date(at);
  return `${d.getHours()}:${pad(d.getMinutes())}`;
}
