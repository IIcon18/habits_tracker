/**
 * Состояние приложения: привычки, отметки и черновик создания.
 *
 * Источник данных — API бэкенда (внутри Telegram или при VITE_USE_API=1),
 * иначе демо-данные из demo.ts (для вёрстки в браузере; ?demo=… тоже включает демо).
 * Отметки оптимистичные: карточка обновляется сразу, при ошибке сервера откатывается.
 * TODO: черновик — в Telegram CloudStorage; отметки без сети — в очередь (экран 9.2).
 */
import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { api } from './api';
import { todayISO } from './date';
import { loadDemo } from './demo';
import { haptic, insideTelegram, tg } from './telegram';
import type { Habit, Mark, MarkKind } from './types';

export interface Draft {
  identity: string;
  full: string;
  mini: string;
  anchor: string;
  reward: string;
}

export const emptyDraft: Draft = { identity: '', full: '', mini: '', anchor: '', reward: '' };

const demoMode =
  new URLSearchParams(location.search).has('demo') || !(insideTelegram || import.meta.env.VITE_USE_API === '1');

interface Data {
  habits: Habit[];
  marks: Mark[];
}

interface Store extends Data {
  /** false, пока привычки грузятся с сервера. */
  loaded: boolean;
  /** Не удалось загрузить привычки. */
  loadError: boolean;
  mark: (habitId: string, kind: MarkKind) => void;
  undo: (habitId: string) => void;
  resume: (habitId: string) => void;
  draft: Draft;
  updateDraft: (patch: Partial<Draft>) => void;
  /** Создаёт привычку из черновика. Черновик не трогает — его очищает resetDraft. */
  createFromDraft: (withReward: boolean) => Promise<Habit>;
  resetDraft: () => void;
}

const StoreContext = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<Data>(() => (demoMode ? loadDemo() : { habits: [], marks: [] }));
  const [loaded, setLoaded] = useState(demoMode);
  const [loadError, setLoadError] = useState(false);
  const [draft, setDraft] = useState<Draft>(emptyDraft);

  /** Отметки и отмены, ещё не подтверждённые сервером, и счётчик всех начатых. */
  const pending = useRef(0);
  const started = useRef(0);
  const loadedOnce = useRef(false);
  /** Перечитать данные с сервера — после ошибки, чтобы экран совпал с сервером. */
  const refresh = useRef(() => {});
  /** Очередь запросов по привычке: «Отметить» и «Отменить» уходят строго по порядку нажатий. */
  const queues = useRef(new Map<string, Promise<unknown>>());

  useEffect(() => {
    if (demoMode) return;
    const load = () => {
      const startedBefore = started.current;
      api.habits().then(
        (d) => {
          // Пока шёл запрос, могла появиться оптимистичная отметка, которой в ответе нет, — тогда ответ пропускаем.
          if (pending.current === 0 && started.current === startedBefore) setData(d);
          loadedOnce.current = true;
          setLoaded(true);
          setLoadError(false);
        },
        () => {
          // Ошибку показываем, только если данных ещё нет; иначе оставляем то, что на экране.
          if (!loadedOnce.current) setLoadError(true);
        },
      );
    };
    refresh.current = load;
    load();
    // Mini App не закрывается, пока человек в чате. Возвращаясь, перечитываем: отметки из бота, новый день.
    const onVisible = () => document.visibilityState === 'visible' && load();
    document.addEventListener('visibilitychange', onVisible);
    tg?.onEvent('activated', load);
    return () => {
      document.removeEventListener('visibilitychange', onVisible);
      tg?.offEvent('activated', load);
    };
  }, []);

  /**
   * Запрос, меняющий отметки привычки. Встаёт в очередь за предыдущим запросом по ней же:
   * иначе быстрые «Отметить» → «Отменить» могли бы дойти до сервера в обратном порядке.
   * Пока запросы идут, перечитанные данные не применяем.
   */
  const track = <T,>(habitId: string, send: () => Promise<T>): Promise<T> => {
    pending.current += 1;
    started.current += 1;
    const prev = queues.current.get(habitId) ?? Promise.resolve();
    const request = prev.catch(() => {}).then(send);
    queues.current.set(habitId, request);
    return request.finally(() => {
      pending.current -= 1;
      if (queues.current.get(habitId) === request) queues.current.delete(habitId);
    });
  };

  /** Запрос не прошёл: откатываем и сверяемся с сервером. */
  const failed = (rollback: () => void) => {
    rollback();
    haptic.error();
    refresh.current();
  };

  const store = useMemo<Store>(() => {
    const today = todayISO();

    /** Заменить привычку и её отметки ответом сервера. */
    const replaceHabit = (habit: Habit, marks: Mark[]) =>
      setData((d) => ({
        habits: d.habits.some((h) => h.id === habit.id)
          ? d.habits.map((h) => (h.id === habit.id ? habit : h))
          : [...d.habits, habit],
        marks: [...d.marks.filter((m) => m.habitId !== habit.id), ...marks],
      }));
    const addMark = (mark: Mark) =>
      setData((d) => ({
        ...d,
        marks: [...d.marks.filter((m) => !(m.habitId === mark.habitId && m.date === mark.date)), mark],
      }));
    const removeMark = (habitId: string) =>
      setData((d) => ({ ...d, marks: d.marks.filter((m) => !(m.habitId === habitId && m.date === today)) }));

    return {
      ...data,
      loaded,
      loadError,
      draft,

      mark: (habitId, kind) => {
        const mark: Mark = { habitId, date: today, kind, at: Date.now() };
        addMark(mark);
        if (demoMode) return;
        // TODO: тост «Отметка не сохранилась» с «Повторить» (экран 9.3).
        track(habitId, () => api.mark(habitId, today, kind, mark.at)).catch(() => failed(() => removeMark(habitId)));
      },

      undo: (habitId) => {
        const prev = data.marks.find((m) => m.habitId === habitId && m.date === today);
        removeMark(habitId);
        if (demoMode || !prev) return;
        track(habitId, () => api.unmark(habitId, today)).catch(() => failed(() => addMark(prev)));
      },

      resume: (habitId) => {
        if (demoMode) {
          setData((d) => ({
            ...d,
            habits: d.habits.map((h) =>
              h.id === habitId
                ? { ...h, status: 'active', pauses: h.pauses.map((p) => (p.end === null ? { ...p, end: today } : p)) }
                : h,
            ),
          }));
          return;
        }
        // Второе нажатие, пока первое не дошло, сервер отклонил бы — не отправляем.
        if (queues.current.has(habitId)) return;
        track(habitId, () => api.resume(habitId)).then(
          ({ habit, marks }) => replaceHabit(habit, marks),
          () => failed(() => {}),
        );
      },

      updateDraft: (patch) => setDraft((d) => ({ ...d, ...patch })),

      createFromDraft: async (withReward) => {
        const input = {
          identity: draft.identity.trim(),
          full: draft.full.trim(),
          mini: draft.mini.trim(),
          anchor: draft.anchor.trim(),
          reward: withReward && draft.reward.trim() ? draft.reward.trim() : null,
        };
        if (demoMode) {
          const habit: Habit = {
            id: crypto.randomUUID(),
            ...input,
            status: 'active',
            pauses: [],
            createdAt: today,
          };
          replaceHabit(habit, []);
          return habit;
        }
        const { habit, marks } = await api.create(input);
        replaceHabit(habit, marks);
        return habit;
      },

      resetDraft: () => setDraft(emptyDraft),
    };
  }, [data, loaded, loadError, draft]);

  return <StoreContext.Provider value={store}>{children}</StoreContext.Provider>;
}

export function useStore(): Store {
  const store = useContext(StoreContext);
  if (!store) throw new Error('useStore вне StoreProvider');
  return store;
}
