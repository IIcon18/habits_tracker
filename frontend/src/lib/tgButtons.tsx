/**
 * Системные кнопки Telegram: MainButton, SecondaryButton, BackButton (design/07-telegram.md).
 * Экран объявляет их хуками, а сами кнопки рисует Telegram.
 *
 * Вне Telegram (разработка в браузере) MainButton и SecondaryButton заменяет
 * DevBottomBar — только для отладки, в Telegram он не рендерится.
 * «Назад» в браузере — обычная кнопка «назад» браузера.
 */
import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { insideTelegram, tg } from './telegram';
import './tgButtons.css';

export interface ButtonSpec {
  text: string;
  /** Неактивная кнопка видна, но не нажимается. По умолчанию активна. */
  active?: boolean;
  onClick: () => void;
}

const cssVar = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function mainParams(spec: ButtonSpec) {
  const active = spec.active ?? true;
  return {
    text: spec.text,
    color: cssVar(active ? '--accent' : '--surface-sunk'),
    text_color: cssVar(active ? '--on-accent' : '--ink-muted'),
    is_active: active,
    is_visible: true,
  };
}

function secondaryParams(spec: ButtonSpec) {
  return {
    text: spec.text,
    color: cssVar('--accent-soft'),
    text_color: cssVar('--on-accent-soft'),
    is_active: spec.active ?? true,
    is_visible: true,
    position: 'left' as const,
  };
}

/* ---------- запасной вариант для браузера ---------- */

interface DevBar {
  setMain: (s: ButtonSpec | null) => void;
  setSecondary: (s: ButtonSpec | null) => void;
}

const DevBarContext = createContext<DevBar | null>(null);

export function TelegramButtonsProvider({ children }: { children: ReactNode }) {
  const [main, setMain] = useState<ButtonSpec | null>(null);
  const [secondary, setSecondary] = useState<ButtonSpec | null>(null);
  // Сеттеры стабильны — значение контекста не меняется между рендерами.
  const setters = useMemo(() => ({ setMain, setSecondary }), []);
  return (
    <DevBarContext.Provider value={setters}>
      {children}
      {!insideTelegram && main && <DevBottomBar main={main} secondary={secondary} />}
    </DevBarContext.Provider>
  );
}

function DevBottomBar({ main, secondary }: { main: ButtonSpec; secondary: ButtonSpec | null }) {
  const mainActive = main.active ?? true;
  return (
    <div className="dev-bar" data-dev-only>
      {secondary && (
        <button type="button" className="dev-bar__btn dev-bar__btn--secondary t-button" onClick={secondary.onClick}>
          {secondary.text}
        </button>
      )}
      <button
        type="button"
        className={`dev-bar__btn t-button${mainActive ? '' : ' dev-bar__btn--off'}`}
        disabled={!mainActive}
        onClick={main.onClick}
      >
        {main.text}
      </button>
    </div>
  );
}

/* ---------- хуки ---------- */

/** Последняя версия колбэка, чтобы не переподписываться на каждый рендер. */
function useLatest<T>(value: T) {
  const ref = useRef(value);
  ref.current = value;
  return ref;
}

function useBottomButton(kind: 'main' | 'secondary', spec: ButtonSpec | null) {
  const dev = useContext(DevBarContext);
  const latest = useLatest(spec);
  const text = spec?.text;
  const active = spec?.active ?? true;
  const shown = spec !== null;

  useEffect(() => {
    if (!shown) return;
    const click = () => latest.current?.onClick();

    if (!insideTelegram) {
      const proxy: ButtonSpec = { text: text!, active, onClick: click };
      (kind === 'main' ? dev?.setMain : dev?.setSecondary)?.(proxy);
      return () => (kind === 'main' ? dev?.setMain : dev?.setSecondary)?.(null);
    }

    if (kind === 'secondary' && !tg!.isVersionAtLeast('7.10')) return;
    const button = kind === 'main' ? tg!.MainButton : tg!.SecondaryButton;
    const spec: ButtonSpec = { text: text!, active, onClick: click };
    const apply = () => button.setParams(kind === 'main' ? mainParams(spec) : secondaryParams(spec));
    apply();
    button.onClick(click);
    tg!.onEvent('themeChanged', apply);
    return () => {
      button.offClick(click);
      tg!.offEvent('themeChanged', apply);
      button.hide();
    };
  }, [kind, shown, text, active, dev, latest]);
}

export const useMainButton = (spec: ButtonSpec | null) => useBottomButton('main', spec);
export const useSecondaryButton = (spec: ButtonSpec | null) => useBottomButton('secondary', spec);

/** Показывает системную кнопку «Назад», пока экран открыт. null — скрыть. */
export function useBackButton(onBack: (() => void) | null) {
  const latest = useLatest(onBack);
  const shown = onBack !== null;

  useEffect(() => {
    if (!insideTelegram || !shown) return;
    const click = () => latest.current?.();
    tg!.BackButton.onClick(click);
    tg!.BackButton.show();
    return () => {
      tg!.BackButton.offClick(click);
      tg!.BackButton.hide();
    };
  }, [shown, latest]);
}
