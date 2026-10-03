import { useMemo, useState } from 'react';
import { DayHeader } from '../components/DayHeader';
import { HabitCard, PausedCard } from '../components/HabitCard';
import { dayMonthLabel, todayISO } from '../lib/date';
import { loadDemo } from '../lib/demo';
import { computeStats } from '../lib/stats';
import { haptic } from '../lib/telegram';
import type { Habit, Mark, MarkKind } from '../lib/types';
import './Today.css';

export function Today() {
  const today = todayISO();
  const [{ habits, marks }, setData] = useState(loadDemo);
  /** Привычка, отмеченная только что, — для анимации капли. */
  const [justMarked, setJustMarked] = useState<string | null>(null);

  const active = habits.filter((h) => h.status === 'active');
  const paused = habits.filter((h) => h.status === 'paused');

  const stats = useMemo(
    () => new Map(habits.map((h) => [h.id, computeStats(h, marks, today)])),
    [habits, marks, today],
  );
  const doneToday = active.filter((h) => stats.get(h.id)!.todayMark).length;

  function mark(habit: Habit, kind: MarkKind) {
    haptic.tap();
    const next: Mark = { habitId: habit.id, date: today, kind, at: Date.now() };
    setData((d) => ({ ...d, marks: [...d.marks, next] }));
    setJustMarked(habit.id);
    // TODO: отправка на сервер; при ошибке — откат и тост 9.3.
    haptic.success();
  }

  function undo(habit: Habit) {
    setData((d) => ({ ...d, marks: d.marks.filter((m) => !(m.habitId === habit.id && m.date === today)) }));
    if (justMarked === habit.id) setJustMarked(null);
  }

  function resume(habit: Habit) {
    setData((d) => ({
      ...d,
      habits: d.habits.map((h) => (h.id === habit.id ? { ...h, status: 'active', pausedAt: undefined } : h)),
    }));
  }

  return (
    <main className="today">
      <DayHeader date={today} done={doneToday} total={active.length} />

      <div className="today__list">
        {active.map((h) => (
          <HabitCard
            key={h.id}
            habit={h}
            stats={stats.get(h.id)!}
            justMarked={justMarked === h.id}
            onMark={(kind) => mark(h, kind)}
            onUndo={() => undo(h)}
          />
        ))}
      </div>

      {paused.length > 0 && (
        <>
          <h2 className="today__section t-meta">На паузе</h2>
          <div className="today__list">
            {paused.map((h) => (
              <PausedCard
                key={h.id}
                habit={h}
                votes={stats.get(h.id)!.votes}
                pausedLabel={h.pausedAt ? dayMonthLabel(h.pausedAt) : ''}
                onResume={() => resume(h)}
              />
            ))}
          </div>
          <p className="today__foot">
            Пока привычка на паузе, она не считается в прогрессе дня и бот о ней не напоминает.
          </p>
        </>
      )}

      {paused.length === 0 && active.length >= 2 && (
        <p className="today__foot">
          Двух привычек хватает, чтобы заметить сдвиг. Третью добавь, когда эти станут привычными.
        </p>
      )}
    </main>
  );
}
