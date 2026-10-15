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

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'X-Timezone': Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
  if (tg?.initData) headers.Authorization = `tma ${tg.initData}`;
  return headers;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers = authHeaders();
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

const RETRY_MIN = 1000;
const RETRY_MAX = 30_000;
/** Сервер шлёт ping раз в 25 с. Если тишина дольше, соединение мёртвое, хоть и не закрыто: обрыв сети, прокси. */
const STALE_MS = 60_000;

/**
 * Поток событий сервера (GET /api/events): onChange — «данные изменились, перечитай».
 * Так отметка из бота сразу видна в открытом приложении. EventSource не умеет заголовок
 * Authorization, поэтому поток читаем через fetch. Обрыв или тишина дольше STALE_MS — переподключение с паузой;
 * после переподключения тоже зовём onChange: пока связи не было, события могли потеряться.
 * Возвращает функцию отписки.
 */
export function watchChanges(onChange: () => void): () => void {
  const abort = new AbortController();
  const { signal } = abort;
  const wait = (ms: number) =>
    new Promise<void>((resolve) => {
      const timer = setTimeout(resolve, ms);
      signal.addEventListener('abort', () => (clearTimeout(timer), resolve()), { once: true });
    });

  (async () => {
    let retry = RETRY_MIN;
    let connectedBefore = false;
    while (!signal.aborted) {
      const connection = new AbortController();
      const stop = () => connection.abort();
      signal.addEventListener('abort', stop, { once: true });
      let watchdog = setTimeout(stop, STALE_MS);
      try {
        const res = await fetch(`${BASE}/events`, {
          headers: authHeaders(),
          signal: connection.signal,
          cache: 'no-store',
        });
        if (!res.ok || !res.body) throw new ApiError(res.status, res.statusText);
        if (connectedBefore) onChange();
        connectedBefore = true;
        retry = RETRY_MIN;

        const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
        let buffer = '';
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          clearTimeout(watchdog);
          watchdog = setTimeout(stop, STALE_MS);
          buffer += value;
          // События разделены пустой строкой; нам важен только тип changed.
          let end: number;
          while ((end = buffer.indexOf('\n\n')) >= 0) {
            if (buffer.slice(0, end).split('\n').includes('event: changed')) onChange();
            buffer = buffer.slice(end + 2);
          }
        }
      } catch {
        /* сеть пропала, сервер перезапускается или сработал watchdog — переподключимся */
      } finally {
        clearTimeout(watchdog);
        signal.removeEventListener('abort', stop);
      }
      await wait(retry);
      retry = Math.min(retry * 2, RETRY_MAX);
    }
  })();

  return () => abort.abort();
}
