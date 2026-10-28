import { useState, type ReactNode } from 'react';
import { Navigate, useLocation, useNavigate, useParams } from 'react-router';
import { daysLabel, Toggle, WeekdayPicker } from '../components/Controls';
import { TimeSheet } from '../components/TimeSheet';
import { shortTime } from '../lib/date';
import { useStore } from '../lib/store';
import { haptic, requestWriteAccess } from '../lib/telegram';
import { useBackButton, useMainButton } from '../lib/tgButtons';
import type { Habit, Reminder as ReminderSettings } from '../lib/types';
import '../components/List.css';
import './Reminder.css';

/**
 * Экран напоминания — screens/6.1, лист времени 6.2, бот без доступа 8.4.
 * Отличие от макета: два напоминания, каждое можно выключить. Основное — в выбранное время,
 * «если не отмечено» — в своё время (по умолчанию 21:00, как на макете). Оба приходят,
 * только если сегодня ещё нет отметки.
 */

const DEFAULT: ReminderSettings = {
  time: '07:45',
  days: [1, 2, 3, 4, 5, 6, 7],
  morning: true,
  evening: true,
  eveningTime: '21:00',
};

const QUICK_TIMES = ['07:00', '07:30', '07:45', '08:00', '08:30'];

const short = shortTime;

/** Почему нельзя сохранить; null — можно. */
function problem(r: ReminderSettings): string | null {
  if (!r.morning && !r.evening) return 'Включи хотя бы одно напоминание.';
  if (r.morning && r.evening && r.eveningTime <= r.time) {
    return `Поставь время позже основного напоминания — после ${short(r.time)}.`;
  }
  return null;
}

export function Reminder() {
  const { id } = useParams();
  const { habits, loaded } = useStore();
  const habit = habits.find((h) => h.id === id);
  if (!loaded) return null;
  if (!habit) return <Navigate to="/today" replace />;
  return <ReminderScreen habit={habit} />;
}

type Sheet = null | 'time' | 'eveningTime';

function ReminderScreen({ habit }: { habit: Habit }) {
  const navigate = useNavigate();
  const afterCreate = Boolean((useLocation().state as { afterCreate?: boolean } | null)?.afterCreate);
  const { saveReminder, allowsWrite, setAllowsWrite } = useStore();

  const [r, setR] = useState<ReminderSettings>(habit.reminder ?? DEFAULT);
  const update = (patch: Partial<ReminderSettings>) => setR((prev) => ({ ...prev, ...patch }));
  const [sheet, setSheet] = useState<Sheet>(null);
  const [saving, setSaving] = useState(false);
  /** Сохранено, но писать бот не может — экран 8.4. */
  const [savedNoAccess, setSavedNoAccess] = useState(false);

  const blocked = problem(r);

  // После мастера «Назад» — на «Сегодня» (привычка уже создана); иначе — туда, откуда пришли.
  const leave = () => {
    const historyIndex = (window.history.state as { idx?: number } | null)?.idx ?? 0;
    if (afterCreate || historyIndex === 0) navigate('/today', { replace: true });
    else navigate(-1);
  };

  const askAccess = async () => {
    const allowed = await requestWriteAccess();
    setAllowsWrite(allowed);
    return allowed;
  };

  const save = async () => {
    setSaving(true);
    try {
      await saveReminder(habit.id, r);
    } catch {
      haptic.error();
      setSaving(false);
      return;
    }
    // Без согласия Telegram не даст боту писать; если уже разрешено, Telegram ответит сразу, без окна.
    const allowed = allowsWrite === true || (await askAccess());
    setSaving(false);
    if (!allowed) {
      haptic.error();
      setSavedNoAccess(true);
      return;
    }
    haptic.success();
    leave();
  };

  useBackButton(sheet || saving ? null : leave);
  useMainButton(
    sheet
      ? null // на открытом листе своя кнопка «Готово» (05-screens.md, 6.2)
      : savedNoAccess
        ? { text: 'Готово', onClick: leave }
        : { text: 'Сохранить', active: !blocked, progress: saving, onClick: save },
  );

  const firstTime = r.morning ? r.time : r.eveningTime;
  const accessBanner = (
    <WriteAccessBanner
      onAllow={async () => {
        if ((await askAccess()) && savedNoAccess) {
          haptic.success();
          leave();
        }
      }}
    />
  );

  if (savedNoAccess) {
    return (
      <main className="reminder">
        <h1 className="t-screen">Напоминание</h1>
        {allowsWrite === false && accessBanner}
        <div className="reminder__time reminder__time--muted">{firstTime}</div>
        <p className="reminder__days-note">{daysLabel(r.days)}</p>
        <p className="reminder__saved t-body">
          Время сохранено. Как только разрешишь, первое напоминание придёт завтра в {short(firstTime)}.
        </p>
      </main>
    );
  }

  return (
    <main className="reminder">
      <h1 className="t-screen">Напоминание</h1>
      <p className="reminder__sub t-body">
        Для «Я человек, который {habit.identity}». Лучше всего — сразу после якоря: {habit.anchor}.
      </p>

      {allowsWrite === false && accessBanner}

      {r.morning && (
        <section className="reminder__main" aria-label="Основное напоминание">
          <button
            type="button"
            className="reminder__time"
            aria-label={`Время напоминания ${r.time}, изменить`}
            onClick={() => setSheet('time')}
          >
            {r.time}
          </button>
          <button type="button" className="reminder__change" onClick={() => setSheet('time')}>
            Изменить время
          </button>
          <div className="reminder__chips">
            {QUICK_TIMES.map((t) => (
              <button
                key={t}
                type="button"
                className={`chip reminder__chip${t === r.time ? ' chip--on' : ''}`}
                aria-pressed={t === r.time}
                onClick={() => {
                  haptic.selection();
                  update({ time: t });
                }}
              >
                {short(t)}
              </button>
            ))}
          </div>
        </section>
      )}

      <div className="reminder__days-head">
        <h2 className="reminder__label">Дни</h2>
        <span className="reminder__days-note">{daysLabel(r.days)}</span>
      </div>
      <WeekdayPicker value={r.days} onChange={(days) => update({ days })} />

      <div className="list-group">
        <div className="list-row">
          <div className="list-row__text">
            Сразу после якоря
            <small>в {short(r.time)}, если ещё не отмечено</small>
          </div>
          <Toggle on={r.morning} onChange={(morning) => update({ morning })} label="Сразу после якоря" />
        </div>
      </div>

      <div className="list-group">
        <div className="list-row">
          <div className="list-row__text">
            Если не отмечено
            <small>в {short(r.eveningTime)} мягко напомню про две минуты</small>
          </div>
          <Toggle on={r.evening} onChange={(evening) => update({ evening })} label="Если не отмечено" />
        </div>
        {r.evening && (
          <button type="button" className="list-row list-row--button" onClick={() => setSheet('eveningTime')}>
            <span className="list-row__text">Время</span>
            <span className="list-row__value">{short(r.eveningTime)}</span>
          </button>
        )}
      </div>

      {blocked && (
        <p className="reminder__problem t-caption" role="status">
          {blocked}
        </p>
      )}

      <h2 className="reminder__label reminder__label--preview">Так придёт сообщение</h2>
      {r.morning && (
        <MessagePreview caption={`в ${short(r.time)}`} habit={habit}>
          <p>После того как {habit.anchor} — самое время.</p>
          <p className="message-preview__gap">
            Полная версия: <b>{habit.full}</b>
          </p>
          <p>
            На две минуты: <b>{habit.mini}</b>
          </p>
        </MessagePreview>
      )}
      {r.evening && (
        <MessagePreview caption={`в ${short(r.eveningTime)}, если не отмечено`} habit={habit}>
          <p>Сегодня ещё без капли. Хватит и двух минут.</p>
          <p className="message-preview__gap">
            На две минуты: <b>{habit.mini}</b>
          </p>
        </MessagePreview>
      )}

      {sheet && (
        <TimeSheet
          value={r[sheet]}
          onClose={() => setSheet(null)}
          onDone={(value) => {
            update({ [sheet]: value });
            setSheet(null);
          }}
        />
      )}
    </main>
  );
}

/** Сообщение бота так, как оно придёт (тексты — app/bot/texts.py). */
function MessagePreview({ caption, habit, children }: { caption: string; habit: Habit; children: ReactNode }) {
  return (
    <figure className="message-preview">
      <figcaption className="message-preview__caption t-caption">{caption}</figcaption>
      <div className="message-preview__bubble t-body">
        <b>Я человек, который {habit.identity}</b>
        {children}
      </div>
    </figure>
  );
}

/** Экран 8.4: плашка --amber-soft и кнопка «Разрешить сообщения». */
function WriteAccessBanner({ onAllow }: { onAllow: () => void }) {
  return (
    <section className="access-banner" role="note">
      <h2 className="access-banner__title">Бот пока не может тебе писать</h2>
      <p className="access-banner__text t-body">
        Telegram разрешает ботам писать только после согласия. Без него напоминания не придут, а отмечать в
        приложении можно как раньше.
      </p>
      <button type="button" className="access-banner__button t-button" onClick={onAllow}>
        Разрешить сообщения
      </button>
    </section>
  );
}
