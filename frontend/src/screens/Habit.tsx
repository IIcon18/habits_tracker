import { useEffect, useMemo, useRef, useState } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router';
import { AiSuggestion } from '../components/AiSuggestion';
import { daysLabel } from '../components/Controls';
import { BottomSheet } from '../components/BottomSheet';
import { DayRow } from '../components/DayRow';
import { Chips, Field } from '../components/Form';
import type { HabitPatch } from '../lib/api';
import { dayMonthLabel, fromISODate, shortTime } from '../lib/date';
import { ANCHOR_CHIPS, IDENTITY_CHIPS, MINI_PLACEHOLDER, REWARD_CHIPS, REWARD_PLACEHOLDER, STEPS } from '../lib/habitCopy';
import { daysWord, votesWord } from '../lib/plural';
import { computeStats } from '../lib/stats';
import { useStore } from '../lib/store';
import { haptic, showPopup } from '../lib/telegram';
import { useBackButton, useMainButton } from '../lib/tgButtons';
import type { Habit as HabitData, Reminder } from '../lib/types';
import '../components/List.css';
import './Habit.css';

/**
 * Экран привычки — screens/6.3. Удаление — нижний лист с выбором (по просьбе вместо системного окна 6.4).
 * Поле открывает редактор как в мастере; правки копятся и уходят на сервер по «Сохранить»
 * (неактивна без изменений). Пока правки не сохранены, они лежат в store — переживают переход
 * на экран напоминания.
 */

type FieldName = 'identity' | 'full' | 'mini' | 'anchor' | 'reward';
type Values = Pick<HabitData, FieldName>;

const FIELDS: { name: FieldName; label: string }[] = [
  { name: 'identity', label: 'Кем хочешь стать' },
  { name: 'full', label: 'Полная версия' },
  { name: 'mini', label: 'На две минуты' },
  { name: 'anchor', label: 'После чего' },
  { name: 'reward', label: 'Награда' },
];

const STEP_OF: Record<FieldName, keyof typeof STEPS> = { identity: 1, full: 2, mini: 2, anchor: 3, reward: 4 };

/** «7:45, каждый день» / «21:00, если не отмечено» */
function reminderLabel(r: Reminder | null | undefined): string {
  if (!r) return 'выключено';
  if (r.morning) return `${shortTime(r.time)}, ${daysLabel(r.days)}`;
  return `${shortTime(r.eveningTime)}, если не отмечено`;
}

/** «Со 2 октября» → «со 2 октября» для середины фразы. */
const since = (d: string) => `${fromISODate(d).getDate() === 2 ? 'со' : 'с'} ${dayMonthLabel(d)}`;

/** Текст листа удаления — как в окне 6.4. */
function deleteMessage(identity: string, votes: number): string {
  const lost = votes > 0 ? ` и ${votesWord(votes)} пропадут насовсем.` : ' пропадёт насовсем.';
  return `«Я человек, который ${identity}»${lost} Если нужен перерыв, лучше поставить на паузу.`;
}

export function Habit() {
  const { id } = useParams();
  const { habits, loaded } = useStore();
  const habit = habits.find((h) => h.id === id);
  if (!loaded) return null;
  if (!habit) return <Navigate to="/today" replace />;
  return <HabitScreen habit={habit} />;
}

function HabitScreen({ habit }: { habit: HabitData }) {
  const navigate = useNavigate();
  const { marks, today, edits, setEdits, updateHabit, pause, resume, removeHabit } = useStore();
  const patch = edits[habit.id] ?? {};
  const values: Values = { ...habit, ...patch };
  const dirty = Object.keys(patch).length > 0;
  const [editing, setEditing] = useState<FieldName | null>(null);
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const scrollBeforeEdit = useRef(0);

  const stats = useMemo(() => computeStats(habit, marks, today), [habit, marks, today]);

  const leave = () => {
    const historyIndex = (window.history.state as { idx?: number } | null)?.idx ?? 0;
    if (historyIndex > 0) navigate(-1);
    else navigate('/today', { replace: true });
  };

  const back = async () => {
    if (dirty) {
      const choice = await showPopup({
        message: 'Изменения не сохранятся.',
        buttons: [{ id: 'leave', type: 'destructive', text: 'Выйти' }, { type: 'cancel' }],
      });
      if (choice !== 'leave') return;
      setEdits(habit.id, null);
    }
    leave();
  };

  /** Записать правку поля: совпала с сохранённым — правки по нему нет. */
  const applyField = (name: FieldName, raw: string) => {
    const value = name === 'reward' ? raw.trim() || null : raw.trim();
    const next: HabitPatch = { ...patch };
    if ((habit[name] ?? null) === value) delete next[name];
    else next[name] = value as never;
    setEdits(habit.id, Object.keys(next).length ? next : null);
  };

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    try {
      await action();
      haptic.success();
      return true;
    } catch {
      haptic.error();
      return false;
    } finally {
      setBusy(false);
    }
  };

  const save = () =>
    run(async () => {
      await updateHabit(habit.id, patch);
      setEdits(habit.id, null);
    });

  const doPause = async () => {
    const done = await run(async () => {
      // Несохранённые правки не теряем: сначала они, потом пауза.
      if (dirty) await updateHabit(habit.id, patch);
      setEdits(habit.id, null);
      await pause(habit.id);
    });
    if (done) navigate('/today', { replace: true });
  };

  const doDelete = async () => {
    const done = await run(async () => {
      await removeHabit(habit.id);
      setEdits(habit.id, null);
    });
    if (done) navigate('/today', { replace: true });
  };

  const closeDelete = () => setDeleting(false);
  useBackButton(editing || busy ? null : deleting ? closeDelete : back);
  // Пока открыт лист удаления, главную кнопку прячем — у листа свои кнопки.
  useMainButton(editing || deleting ? null : { text: 'Сохранить', active: dirty, progress: busy, onClick: save });

  const openEditor = (name: FieldName) => {
    scrollBeforeEdit.current = window.scrollY;
    setEditing(name);
  };
  const closeEditor = () => {
    setEditing(null);
    requestAnimationFrame(() => window.scrollTo(0, scrollBeforeEdit.current));
  };

  if (editing) {
    return (
      <FieldEditor
        name={editing}
        values={values}
        onCancel={closeEditor}
        onDone={(value) => {
          applyField(editing, value);
          closeEditor();
        }}
      />
    );
  }

  return (
    <main className="habit">
      <h1 className="t-screen">Я человек, который {values.identity}</h1>
      <p className="habit__sub t-body">
        {stats.votes > 0
          ? `${votesWord(stats.votes)} ${since(habit.createdAt)} · лучшая серия ${daysWord(stats.bestStreak)}`
          : 'Первый голос — сегодня'}
      </p>

      {/* «Итог за 30 дней ›» откроет экран 7.1, когда он появится; пока — только ряд дней. */}
      <section className="habit__summary" aria-label="Итог за 30 дней">
        <h2 className="habit__summary-title">Итог за 30 дней</h2>
        <DayRow days={stats.days} showScale={false} />
      </section>

      <div className="list-group">
        {FIELDS.map(({ name, label }) => (
          <button key={name} type="button" className="field-row" onClick={() => openEditor(name)}>
            <span className="field-row__label t-caption">{label}</span>
            <span className={`field-row__value${values[name] ? '' : ' field-row__value--empty'}`}>
              {name === 'identity' ? `Я человек, который ${values.identity}` : values[name] || 'Без награды'}
            </span>
          </button>
        ))}
      </div>

      <div className="list-group">
        <button type="button" className="list-row" onClick={() => navigate(`/habit/${habit.id}/reminder`)}>
          <span className="list-row__text">Напоминание</span>
          <span className="list-row__value">{reminderLabel(habit.reminder)}</span>
        </button>
      </div>

      <div className="list-group">
        {habit.status === 'paused' ? (
          <button
            type="button"
            className="list-row"
            disabled={busy}
            onClick={() => {
              resume(habit.id);
              haptic.success();
            }}
          >
            <span className="list-row__text">
              Вернуть
              <small>Серия и голоса сохранены</small>
            </span>
          </button>
        ) : (
          <button type="button" className="list-row list-row--chevron" disabled={busy} onClick={doPause}>
            <span className="list-row__text">
              Поставить на паузу
              <small>Серия и голоса сохранятся</small>
            </span>
          </button>
        )}
        <button type="button" className="list-row list-row--danger" disabled={busy} onClick={() => setDeleting(true)}>
          <span className="list-row__text">Удалить привычку</span>
        </button>
      </div>

      {deleting && (
        <BottomSheet title="Удалить привычку?" onClose={closeDelete}>
          <p className="delete-sheet__text t-body">{deleteMessage(habit.identity, stats.votes)}</p>
          <div className="delete-sheet__actions">
            {habit.status !== 'paused' && (
              <button type="button" className="sheet-action sheet-action--soft t-button" disabled={busy} onClick={doPause}>
                Поставить на паузу
              </button>
            )}
            <button type="button" className="sheet-action sheet-action--danger t-button" disabled={busy} onClick={doDelete}>
              Удалить
            </button>
            <button type="button" className="sheet-action sheet-action--cancel t-button" onClick={closeDelete}>
              Отмена
            </button>
          </div>
        </BottomSheet>
      )}
    </main>
  );
}

interface FieldEditorProps {
  name: FieldName;
  values: Values;
  onDone: (value: string) => void;
  onCancel: () => void;
}

/** Редактор одного поля — те же заголовки, поля и подсказки, что на шаге мастера. */
function FieldEditor({ name, values, onDone, onCancel }: FieldEditorProps) {
  const [value, setValue] = useState(values[name] ?? '');
  const { title, sub } = STEPS[STEP_OF[name]];
  const valid = name === 'reward' || Boolean(value.trim());

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);
  useBackButton(onCancel);
  useMainButton({ text: 'Готово', active: valid, onClick: () => onDone(value) });

  return (
    <main className="habit habit--editor">
      <h1 className="t-screen">{title}</h1>
      <p className="habit__sub t-body">{sub}</p>
      <div className="habit__editor-body">
        {name === 'identity' && (
          <>
            <Field display prefix="Я человек, который" value={value} onChange={setValue} autoFocus />
            <Chips options={IDENTITY_CHIPS} value={value} onPick={setValue} />
          </>
        )}
        {name === 'full' && <Field label="Полная версия" value={value} onChange={setValue} autoFocus />}
        {name === 'mini' && (
          <>
            <Field label="На две минуты" placeholder={MINI_PLACEHOLDER} value={value} onChange={setValue} autoFocus />
            <AiSuggestion full={values.full} value={value} onPick={setValue} />
          </>
        )}
        {name === 'anchor' && (
          <>
            <Field prefix="После того как" ariaLabel="После того как" value={value} onChange={setValue} autoFocus />
            <Chips options={ANCHOR_CHIPS} value={value} onPick={setValue} />
          </>
        )}
        {name === 'reward' && (
          <>
            <Field ariaLabel="Награда" placeholder={REWARD_PLACEHOLDER} value={value} onChange={setValue} autoFocus />
            <Chips options={REWARD_CHIPS} value={value} onPick={setValue} />
          </>
        )}
      </div>
    </main>
  );
}
