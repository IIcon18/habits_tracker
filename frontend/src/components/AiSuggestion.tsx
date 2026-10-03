import { useEffect, useRef, useState } from 'react';
import { suggestMini } from '../lib/ai';
import { haptic } from '../lib/telegram';
import './AiSuggestion.css';

interface AiSuggestionProps {
  /** Полная версия, для которой подбираем «две минуты». */
  full: string;
  /** Текущее значение поля «На две минуты». */
  value: string;
  onPick: (value: string) => void;
}

type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; options: string[] };

/** Подсказка ИИ — design/04-components.md, AiSuggestion; эталоны screens/5.2 и 4.2. */
export function AiSuggestion({ full, value, onPick }: AiSuggestionProps) {
  const [state, setState] = useState<State>({ status: 'idle' });
  const [page, setPage] = useState(0);
  const request = useRef(0);
  const latest = useRef({ value, onPick });
  latest.current = { value, onPick };

  const query = full.trim();

  useEffect(() => {
    if (!query) {
      setState({ status: 'idle' });
      return;
    }
    const id = ++request.current;
    setState({ status: 'loading' });
    // Небольшая пауза, чтобы не дёргать ИИ на каждую букву.
    const timer = setTimeout(() => {
      suggestMini(query, page).then(
        (options) => {
          if (id !== request.current) return;
          setState({ status: 'ready', options });
          // Первый вариант сразу подставляем, если человек ещё ничего не написал сам.
          if (!latest.current.value.trim()) latest.current.onPick(options[0]);
        },
        () => id === request.current && setState({ status: 'error' }),
      );
    }, 500);
    return () => clearTimeout(timer);
  }, [query, page]);

  // Ошибка ИИ или пустая полная версия — блок просто не показывается.
  if (state.status === 'idle' || state.status === 'error') return null;

  return (
    <section className="ai" aria-label="Подсказка ИИ" aria-busy={state.status === 'loading'}>
      <header className="ai__head">
        <i className="ai__mark" aria-hidden="true" />
        <span className="ai__title">Подсказка ИИ</span>
        <span className="ai__for">{state.status === 'loading' ? 'подбираю…' : `для «${query}»`}</span>
      </header>

      {state.status === 'loading' ? (
        <>
          <div className="ai__list" aria-hidden="true">
            <i className="ai__placeholder" />
            <i className="ai__placeholder" />
            <i className="ai__placeholder" />
          </div>
          <p className="ai__foot">Пока я думаю, можно написать свой вариант.</p>
        </>
      ) : (
        <>
          <div className="ai__list">
            {state.options.map((option) => {
              const on = option === value.trim();
              return (
                <button
                  key={option}
                  type="button"
                  className={`ai__option${on ? ' ai__option--on' : ''}`}
                  aria-pressed={on}
                  onClick={() => {
                    haptic.selection();
                    onPick(option);
                  }}
                >
                  <span>{option}</span>
                  <small>{on ? 'Выбрано' : 'Взять'}</small>
                </button>
              );
            })}
          </div>
          <div className="ai__foot ai__foot--row">
            <span>Это черновик — поправь под себя</span>
            <button type="button" className="ai__more" onClick={() => setPage((p) => p + 1)}>
              Ещё варианты
            </button>
          </div>
        </>
      )}
    </section>
  );
}
