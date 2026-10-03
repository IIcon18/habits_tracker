import { useId } from 'react';
import { haptic } from '../lib/telegram';
import './Form.css';

interface FieldProps {
  value: string;
  onChange: (value: string) => void;
  /** Подпись над полем: «Полная версия». */
  label?: string;
  /** Префикс внутри поля: «Я человек, который». */
  prefix?: string;
  placeholder?: string;
  /** Поле идентичности — шрифт Unbounded. */
  display?: boolean;
  autoFocus?: boolean;
  ariaLabel?: string;
}

export function Field({ value, onChange, label, prefix, placeholder, display, autoFocus, ariaLabel }: FieldProps) {
  const id = useId();
  return (
    <div className="field">
      {label && (
        <label className="field__label" htmlFor={id}>
          {label}
        </label>
      )}
      <div className={`field__box${display ? ' field__box--display' : ''}`}>
        {prefix && (
          <label className="field__prefix" htmlFor={id}>
            {prefix}
          </label>
        )}
        <input
          id={id}
          className="field__input"
          value={value}
          placeholder={placeholder}
          aria-label={ariaLabel}
          autoFocus={autoFocus}
          autoComplete="off"
          enterKeyHint="next"
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    </div>
  );
}

interface ChipsProps {
  options: string[];
  value: string;
  onPick: (value: string) => void;
}

export function Chips({ options, value, onPick }: ChipsProps) {
  return (
    <div className="chips">
      {options.map((option) => {
        const on = option === value.trim();
        return (
          <button
            key={option}
            type="button"
            className={`chip${on ? ' chip--on' : ''}`}
            aria-pressed={on}
            onClick={() => {
              haptic.selection();
              onPick(option);
            }}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}

export function StepProgress({ step, total }: { step: number; total: number }) {
  return (
    <div className="steps">
      <div className="steps__bars" aria-hidden="true">
        {Array.from({ length: total }, (_, i) => (
          <i key={i} className={i < step ? 'steps__bar steps__bar--on' : 'steps__bar'} />
        ))}
      </div>
      <p className="steps__label t-caption">
        Шаг {step} из {total}
      </p>
    </div>
  );
}

/** «После того как налью утренний кофе, я читаю 30 минут. Или хотя бы прочитать одну страницу.» */
export function PlanPreview({ anchor, full, mini }: { anchor: string; full: string; mini: string }) {
  return (
    <p className="plan-preview">
      <b>После того как {anchor.trim()}</b>, я {full.trim()}. Или хотя бы {mini.trim()}.
    </p>
  );
}
