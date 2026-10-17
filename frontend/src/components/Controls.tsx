import { plural } from '../lib/plural';
import { haptic } from '../lib/telegram';
import './Controls.css';

interface ToggleProps {
  on: boolean;
  onChange: (on: boolean) => void;
  /** Подпись для чтения с экрана, если рядом нет видимой. */
  label: string;
}

/** Toggle — design/04-components.md: 51×31, вкл. --accent, выкл. --line. */
export function Toggle({ on, onChange, label }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      className={`toggle${on ? ' toggle--on' : ''}`}
      onClick={() => {
        haptic.selection();
        onChange(!on);
      }}
    />
  );
}

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

/** «каждый день» / «5 дней в неделю» */
export function daysLabel(days: number[]): string {
  const n = days.length;
  return n === 7 ? 'каждый день' : `${n} ${plural(n, 'день', 'дня', 'дней')} в неделю`;
}

interface WeekdayPickerProps {
  /** 1 (пн) … 7 (вс) */
  value: number[];
  onChange: (days: number[]) => void;
}

/** WeekdayPicker — 7 кнопок 44px. Последний день не снимается: без дней напоминание бессмысленно. */
export function WeekdayPicker({ value, onChange }: WeekdayPickerProps) {
  return (
    <div className="weekdays">
      {WEEKDAYS.map((name, i) => {
        const day = i + 1;
        const on = value.includes(day);
        return (
          <button
            key={day}
            type="button"
            className={`weekdays__day${on ? ' weekdays__day--on' : ''}`}
            aria-pressed={on}
            onClick={() => {
              if (on && value.length === 1) return;
              haptic.selection();
              onChange(on ? value.filter((d) => d !== day) : [...value, day].sort((a, b) => a - b));
            }}
          >
            {name}
          </button>
        );
      })}
    </div>
  );
}
