import type { DayState } from '../lib/stats';
import './DayRow.css';

interface DayCellProps {
  state: DayState;
  today?: boolean;
  /** Только что отмечено — проиграть падение капли. */
  just?: boolean;
}

export function DayCell({ state, today, just }: DayCellProps) {
  const cls = ['day', `day--${state}`, today && 'day--today', just && 'day--just'].filter(Boolean).join(' ');
  return (
    <span className={cls}>
      <i className="day__fill" />
      <i className="day__drop" />
      <i className="day__ripple" />
    </span>
  );
}

const LABELS: Record<DayState, string> = {
  full: 'сделал',
  mini: 'две минуты',
  miss: 'пропуск',
  miss2: 'пропуск',
  'today-empty': 'ещё не отмечено',
  before: 'до начала привычки',
};

interface DayRowProps {
  days: DayState[];
  justMarked?: boolean;
}

export function DayRow({ days, justMarked }: DayRowProps) {
  const last = days.length - 1;
  const summary = `Последние 2 недели: ${days.map((d) => LABELS[d]).join(', ')}`;
  return (
    <>
      <div className="day-row" role="img" aria-label={summary}>
        {days.map((state, i) => (
          <DayCell key={i} state={state} today={i === last} just={i === last && justMarked} />
        ))}
      </div>
      <div className="day-scale t-scale" aria-hidden="true">
        <span>2 недели назад</span>
        <span>сегодня</span>
      </div>
    </>
  );
}
