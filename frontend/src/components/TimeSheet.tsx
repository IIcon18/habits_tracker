import { useLayoutEffect, useRef, useState } from 'react';
import { haptic } from '../lib/telegram';
import { BottomSheet } from './BottomSheet';
import './TimeSheet.css';

/** Высота строки барабана; должна совпадать с --wheel-row в TimeSheet.css. */
const ROW = 44;
const HOURS = Array.from({ length: 24 }, (_, i) => i);
const MINUTES = Array.from({ length: 12 }, (_, i) => i * 5);

const pad = (n: number) => String(n).padStart(2, '0');

interface WheelProps {
  values: number[];
  index: number;
  onIndex: (index: number) => void;
  label: string;
}

/** Барабан на прокрутке со «щелчком» строк: колесо, палец, клавиши ↑↓ и нажатие на строку. */
function Wheel({ values, index, onIndex, label }: WheelProps) {
  const ref = useRef<HTMLDivElement>(null);
  const current = useRef(index);

  useLayoutEffect(() => {
    ref.current!.scrollTop = index * ROW;
    // Только при открытии: дальше положение задаёт прокрутка.
  }, []);

  const select = (i: number) => {
    const next = Math.max(0, Math.min(values.length - 1, i));
    if (next === current.current) return;
    current.current = next;
    haptic.selection();
    onIndex(next);
  };

  const scrollTo = (i: number) => ref.current!.scrollTo({ top: i * ROW, behavior: 'smooth' });

  return (
    <div
      ref={ref}
      className="wheel__column"
      role="listbox"
      aria-label={label}
      aria-activedescendant={`${label}-${values[index]}`}
      tabIndex={0}
      onScroll={(e) => select(Math.round(e.currentTarget.scrollTop / ROW))}
      onKeyDown={(e) => {
        if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;
        e.preventDefault();
        scrollTo(index + (e.key === 'ArrowDown' ? 1 : -1));
      }}
    >
      {values.map((v, i) => (
        <div
          key={v}
          id={`${label}-${v}`}
          role="option"
          aria-selected={i === index}
          className={`wheel__item${i === index ? ' wheel__item--on' : ''}`}
          onClick={() => scrollTo(i)}
        >
          {pad(v)}
        </div>
      ))}
    </div>
  );
}

interface TimeSheetProps {
  /** «07:45» */
  value: string;
  onDone: (value: string) => void;
  onClose: () => void;
}

/** Экран 6.2: нижний лист с барабанами часов и минут (шаг 5 минут). */
export function TimeSheet({ value, onDone, onClose }: TimeSheetProps) {
  const [h, m] = value.split(':').map(Number);
  const [hour, setHour] = useState(h);
  // Время не кратно 5 (например, задано через API) — ближайшее на барабане.
  const [minute, setMinute] = useState(Math.min(11, Math.round(m / 5)));

  return (
    <BottomSheet title="Время напоминания" onClose={onClose}>
      <div className="wheel">
        <Wheel values={HOURS} index={hour} onIndex={setHour} label="часы" />
        <span className="wheel__colon" aria-hidden="true">
          :
        </span>
        <Wheel values={MINUTES} index={minute} onIndex={setMinute} label="минуты" />
      </div>
      <button
        type="button"
        className="sheet__done t-button"
        onClick={() => onDone(`${pad(HOURS[hour])}:${pad(MINUTES[minute])}`)}
      >
        Готово
      </button>
    </BottomSheet>
  );
}
