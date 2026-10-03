/**
 * Состояние приложения: привычки, отметки и черновик создания.
 * Пока всё в памяти на демо-данных; позже здесь будут запросы к бэкенду
 * и сохранение черновика в Telegram CloudStorage (design/07-telegram.md).
 */
import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { todayISO } from './date';
import { loadDemo } from './demo';
import type { Habit, Mark, MarkKind } from './types';

export interface Draft {
  identity: string;
  full: string;
  mini: string;
  anchor: string;
  reward: string;
}

export const emptyDraft: Draft = { identity: '', full: '', mini: '', anchor: '', reward: '' };

interface Store {
  habits: Habit[];
  marks: Mark[];
  mark: (habitId: string, kind: MarkKind) => void;
  undo: (habitId: string) => void;
  resume: (habitId: string) => void;
  draft: Draft;
  updateDraft: (patch: Partial<Draft>) => void;
  /** Создаёт привычку из черновика. Черновик не трогает — его очищает resetDraft. */
  createFromDraft: (withReward: boolean) => Habit;
  resetDraft: () => void;
}

const StoreContext = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [{ habits, marks }, setData] = useState(loadDemo);
  const [draft, setDraft] = useState<Draft>(emptyDraft);

  const store = useMemo<Store>(() => {
    const today = todayISO();
    return {
      habits,
      marks,
      mark: (habitId, kind) =>
        setData((d) => ({ ...d, marks: [...d.marks, { habitId, date: today, kind, at: Date.now() }] })),
      undo: (habitId) =>
        setData((d) => ({ ...d, marks: d.marks.filter((m) => !(m.habitId === habitId && m.date === today)) })),
      resume: (habitId) =>
        setData((d) => ({
          ...d,
          habits: d.habits.map((h) => (h.id === habitId ? { ...h, status: 'active', pausedAt: undefined } : h)),
        })),
      draft,
      updateDraft: (patch) => setDraft((d) => ({ ...d, ...patch })),
      createFromDraft: (withReward) => {
        const habit: Habit = {
          id: crypto.randomUUID(),
          identity: draft.identity.trim(),
          full: draft.full.trim(),
          mini: draft.mini.trim(),
          anchor: draft.anchor.trim(),
          reward: withReward && draft.reward.trim() ? draft.reward.trim() : undefined,
          status: 'active',
          createdAt: today,
        };
        setData((d) => ({ ...d, habits: [...d.habits, habit] }));
        return habit;
      },
      resetDraft: () => setDraft(emptyDraft),
    };
  }, [habits, marks, draft]);

  return <StoreContext.Provider value={store}>{children}</StoreContext.Provider>;
}

export function useStore(): Store {
  const store = useContext(StoreContext);
  if (!store) throw new Error('useStore вне StoreProvider');
  return store;
}
