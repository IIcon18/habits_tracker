import { useMemo, useState } from 'react';
import { Link, Navigate } from 'react-router';
import { DayHeader } from '../components/DayHeader';
import { HabitCard, PausedCard } from '../components/HabitCard';
import { sinceLabel, todayISO } from '../lib/date';
import { computeStats } from '../lib/stats';
import { useStore } from '../lib/store';
import { haptic } from '../lib/telegram';
import type { MarkKind } from '../lib/types';
import './Today.css';

export function Today() {
  const today = todayISO();
  const { habits, marks, loaded, loadError, mark, undo, resume } = useStore();
  /** Привычка, отмеченная только что, — для анимации капли. */
  const [justMarked, setJustMarked] = useState<string | null>(null);

  const active = habits.filter((h) => h.status === 'active');
  const paused = habits.filter((h) => h.status === 'paused');

  const stats = useMemo(
    () => new Map(habits.map((h) => [h.id, computeStats(h, marks, today)])),
    [habits, marks, today],
  );
  const doneToday = active.filter((h) => stats.get(h.id)!.todayMark).length;

  if (loadError) {
    return (
      <main className="today__error">
        <p className="t-body">Похоже, сервер не ответил.</p>
        <button type="button" className="today__add" onClick={() => location.reload()}>
          Повторить
        </button>
      </main>
    );
  }
  if (!loaded) return null;
  // TODO: пустое состояние 2.4; пока сразу ведём в мастер.
  if (habits.length === 0) return <Navigate to="/new/1" replace />;

  function onMark(habitId: string, kind: MarkKind) {
    haptic.tap();
    mark(habitId, kind);
    setJustMarked(habitId);
    haptic.success();
  }

  function onUndo(habitId: string) {
    undo(habitId);
    if (justMarked === habitId) setJustMarked(null);
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
            onMark={(kind) => onMark(h.id, kind)}
            onUndo={() => onUndo(h.id)}
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
                pausedLabel={sinceLabel(h.pauses.find((p) => p.end === null)?.start ?? today)}
                onResume={() => resume(h.id)}
              />
            ))}
          </div>
          <p className="today__foot">
            Пока привычка на паузе, она не считается в прогрессе дня и бот о ней не напоминает.
          </p>
        </>
      )}

      {paused.length === 0 && active.length === 2 && (
        <p className="today__foot">
          Двух привычек хватает, чтобы заметить сдвиг. Третью добавь, когда эти станут привычными.
        </p>
      )}

      {/* TODO: при трёх активных — лист лимита 9.1 вместо перехода. */}
      <Link className="today__add" to="/new/1">
        Добавить привычку
      </Link>
    </main>
  );
}
