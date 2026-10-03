/**
 * Клиент API бэкенда (backend/app). Авторизация — подписанная initData Telegram,
 * сервер её проверяет. Часовой пояс нужен серверу, чтобы знать, какой у человека «сегодня».
 */
import type { ISODate } from './date';
import { tg } from './telegram';
import type { Habit, Mark, MarkKind, Reminder } from './types';

const BASE = '/api';

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {
    'X-Timezone': Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
  if (tg?.initData) headers.Authorization = `tma ${tg.initData}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  const res = await fetch(BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  if (!res.ok) {
    const detail = await res.json().then((j) => j?.detail, () => null);
    throw new ApiError(res.status, typeof detail === 'string' ? detail : res.statusText);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

/* Формат ответа сервера: отметки лежат внутри привычки, время — ISO-строкой. */

interface HabitDto extends Omit<Habit, 'reminder'> {
  marks: { date: ISODate; kind: MarkKind; at: string }[];
  reminder: (Omit<Reminder, 'time'> & { time: string }) | null;
}

function fromDto(dto: HabitDto): { habit: Habit; marks: Mark[] } {
  const { marks, reminder, ...rest } = dto;
  return {
    habit: { ...rest, reminder: reminder && { ...reminder, time: reminder.time.slice(0, 5) } },
    marks: marks.map((m) => ({ habitId: dto.id, date: m.date, kind: m.kind, at: Date.parse(m.at) })),
  };
}

function splitAll(dtos: HabitDto[]): { habits: Habit[]; marks: Mark[] } {
  const parts = dtos.map(fromDto);
  return { habits: parts.map((p) => p.habit), marks: parts.flatMap((p) => p.marks) };
}

export type HabitInput = Pick<Habit, 'identity' | 'full' | 'mini' | 'anchor'> & { reward?: string | null };

export const api = {
  habits: async () => splitAll(await request<HabitDto[]>('GET', '/habits')),
  create: async (input: HabitInput) => fromDto(await request<HabitDto>('POST', '/habits', input)),
  pause: async (id: string) => fromDto(await request<HabitDto>('POST', `/habits/${id}/pause`)),
  resume: async (id: string) => fromDto(await request<HabitDto>('POST', `/habits/${id}/resume`)),
  remove: (id: string) => request<void>('DELETE', `/habits/${id}`),
  mark: (id: string, date: ISODate, kind: MarkKind, at: number) =>
    request<unknown>('PUT', `/habits/${id}/marks/${date}`, { kind, at: new Date(at).toISOString() }),
  unmark: (id: string, date: ISODate) => request<void>('DELETE', `/habits/${id}/marks/${date}`),
};
