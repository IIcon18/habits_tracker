import { dayMonthLabel, weekdayLabel, type ISODate } from '../lib/date';
import './DayHeader.css';

interface DayHeaderProps {
  date: ISODate;
  done: number;
  total: number;
}

export function DayHeader({ date, done, total }: DayHeaderProps) {
  const progress = total > 0 ? done / total : 0;
  const full = total > 0 && done === total;

  return (
    <header className="day-header">
      <div className="day-header__water" style={{ height: `${progress * 100}%` }} aria-hidden="true">
        <svg className="day-header__wave" viewBox="0 0 390 10" preserveAspectRatio="none">
          <path d="M0 10V6C70 1 120 1 195 5S320 9 390 4V10Z" />
        </svg>
      </div>
      <div className="day-header__date">
        <span className="day-header__weekday t-meta">{weekdayLabel(date)}</span>
        <h1 className="t-date">{dayMonthLabel(date)}</h1>
      </div>
      <div className="day-header__progress" aria-live="polite">
        <span className="t-numeral">
          {done} из {total}
        </span>
        <span className="day-header__label">{full ? 'день наполнен' : 'капли сегодня'}</span>
      </div>
    </header>
  );
}
