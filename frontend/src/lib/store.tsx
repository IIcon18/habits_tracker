/**
 * Состояние приложения: привычки, отметки и черновик создания.
 *
 * Источник данных — API бэкенда (внутри Telegram или при VITE_USE_API=1),
 * иначе демо-данные из demo.ts (для вёрстки в браузере; ?demo=… тоже включает демо).
 * Отметки оптимистичные: карточка обновляется сразу, при ошибке сервера откатывается.
 * Изменения из бота и других окон приходят потоком событий сервера — данные перечитываются сразу.
 * TODO: черновик — в Telegram CloudStorage; отметки без сети — в очередь (экран 9.2).
 */
import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { api, watchChanges } from './api';
import { todayISO, type ISODate } from './date';
import { loadDemo } from './demo';
import { haptic, insideTelegram, tg } from './telegram';
import type { Habit, Mark, MarkKind, Reminder } from './types';

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
  /** «Сегодня» на устройстве; меняется в полночь, даже если приложение просто открыто. */
  today: ISODate;
  /** false, пока привычки грузятся с сервера. */
  loaded: boolean;
  /** Не удалось загрузить привычки. */
  loadError: boolean;
  mark: (habitId: string, kind: MarkKind) => void;
  undo: (habitId: string) => void;
  resume: (habitId: string) => void;
  /** Сохраняет напоминание привычки (экран 6.1). */
  saveReminder: (habitId: string, reminder: Reminder) => Promise<void>;
  /** Может ли бот писать: null — неизвестно (или вне Telegram), false — отказ (экран 8.4). */
  allowsWrite: boolean | null;
  setAllowsWrite: (allowed: boolean) => void;
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
  const [today, setToday] = useState<ISODate>(todayISO);
  const [allowsWrite, setAllowsWrite] = useState<boolean | null>(null);

  /** Отметки и отмены, ещё не подтверждённые сервером, и счётчик всех начатых. */
  const pending = useRef(0);
  const started = useRef(0);
  const loadedOnce = useRef(false);
  /** Номер последнего запроса привычек: ответ на более ранний, пришедший позже, не применяем. */
  const loadSeq = useRef(0);
  /** Перечитать данные с сервера — после ошибки, чтобы экран совпал с сервером. */
  const refresh = useRef(() => {});
  /** Очередь запросов по привычке: «Отметить» и «Отменить» уходят строго по порядку нажатий. */
  const queues = useRef(new Map<string, Promise<unknown>>());

  // Без этого после полуночи открытое приложение показывало бы вчерашний день и отправляло отметку вчерашним числом.
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const sync = () => {
      setToday(todayISO());
      clearTimeout(timer);
      const midnight = new Date();
      midnight.setHours(24, 0, 1, 0);
      timer = setTimeout(sync, midnight.getTime() - Date.now());
    };
    sync();
    // Таймеры в свёрнутом приложении могут опаздывать — сверяемся, когда оно снова на экране.
    const onVisible = () => document.visibilityState === 'visible' && sync();
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('focus', sync);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('focus', sync);
    };
  }, []);

  useEffect(() => {
    if (demoMode) return;
    const load = () => {
      const startedBefore = started.current;
      const seq = ++loadSeq.current;
      api.habits().then(
        (d) => {
          if (seq !== loadSeq.current) return;
          // Пока шёл запрос, могла появиться оптимистичная отметка, которой в ответе нет, — тогда ответ пропускаем.
          if (pending.current === 0 && started.current === startedBefore) setData(d);
          loadedOnce.current = true;
          setLoaded(true);
          setLoadError(false);
        },
        () => {
          // Ошибку показываем, только если данных ещё нет; иначе оставляем то, что на экране.
          if (seq === loadSeq.current && !loadedOnce.current) setLoadError(true);
        },
      );
    };
    refresh.current = load;
    load();
    api.me().then(
      (me) => setAllowsWrite(me.allowsWrite),
      () => {},
    );
    // Несколько событий подряд (своя отметка, кнопка в чате) — одно перечитывание.
    let timer: ReturnType<typeof setTimeout> | undefined;
    const soon = () => {
      clearTimeout(timer);
      timer = setTimeout(load, 150);
    };
    // Отметка в чате с ботом или в другом окне — сервер сообщает сразу, пока приложение открыто.
    const stopWatching = watchChanges(soon);
    // Возвращаясь в приложение, тоже перечитываем: поток мог оборваться, пока оно было свёрнуто, или наступил новый день.
    const onVisible = () => document.visibilityState === 'visible' && soon();
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('focus', soon);
    tg?.onEvent('activated', soon);
    return () => {
      clearTimeout(timer);
      stopWatching();
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('focus', soon);
      tg?.offEvent('activated', soon);
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
      today,
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

      saveReminder: async (habitId, reminder) => {
        const saved = demoMode ? reminder : await api.setReminder(habitId, reminder);
        setData((d) => ({ ...d, habits: d.habits.map((h) => (h.id === habitId ? { ...h, reminder: saved } : h)) }));
      },

      allowsWrite,
      setAllowsWrite,

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
  }, [data, today, allowsWrite, loaded, loadError, draft]);

  return <StoreContext.Provider value={store}>{children}</StoreContext.Provider>;
}

export function useStore(): Store {
  const store = useContext(StoreContext);
  if (!store) throw new Error('useStore вне StoreProvider');
  return store;
}
