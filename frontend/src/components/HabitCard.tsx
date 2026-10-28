import { Link } from 'react-router';
import { timeLabel } from '../lib/date';
import { daysWord, votesWord } from '../lib/plural';
import type { HabitStats } from '../lib/stats';
import type { Habit, MarkKind } from '../lib/types';
import { DayRow } from './DayRow';
import './HabitCard.css';

interface HabitCardProps {
  habit: Habit;
  stats: HabitStats;
  /** Отметка сделана только что — проиграть каплю и появление MarkDone. */
  justMarked: boolean;
  onMark?: (kind: MarkKind) => void;
  onUndo?: () => void;
  /** Превью в мастере (5.4): без шкалы и кнопок. */
  preview?: boolean;
}

export function HabitCard({ habit, stats, justMarked, onMark, onUndo, preview }: HabitCardProps) {
  const { votes, streak, missState, todayMark } = stats;
  const twoMisses = missState === 'two';

  return (
    <article className="habit-card">
      <div className="habit-card__head">
        <h2 className="t-identity">
          {preview ? (
            `Я человек, который ${habit.identity}`
          ) : (
            <Link className="habit-card__link" to={`/habit/${habit.id}`}>
              Я человек, который {habit.identity}
            </Link>
          )}
        </h2>
        {!preview && <EditLink habitId={habit.id} />}
      </div>
      <p className="habit-card__plan t-body">
        После того как {habit.anchor} — <b>{habit.full}</b>
        <br />
        или хотя бы {habit.mini}
      </p>

      <DayRow days={stats.days} justMarked={justMarked} showScale={!preview} />

      <div className="habit-card__meta t-meta">
        {votes === 0 ? (
          <span>Первый голос — сегодня</span>
        ) : (
          <>
            <span>{votesWord(votes)}</span>
            <span>{streak > 0 ? `серия ${daysWord(streak)}` : 'серия начнётся заново'}</span>
          </>
        )}
      </div>

      {missState === 'one' && (
        <p className="habit-card__note">Вчера пропуск — это нормально. Сегодня хватит и двух минут.</p>
      )}
      {twoMisses && (
        <div className="habit-card__warn" role="note">
          Два дня без капли
          <span>
            {votes > 0 ? `Голоса никуда не делись — их ${votes}. ` : ''}Вернись с двух минут: {habit.mini}.
          </span>
        </div>
      )}

      {preview ? null : todayMark ? (
        <div className={`mark-done${justMarked ? ' mark-done--just' : ''}`}>
          <div>
            <span className="mark-done__title">
              {todayMark.kind === 'full' ? 'Сделал полностью' : 'Две минуты засчитаны'}
            </span>
            <span className="mark-done__caption t-caption">в {timeLabel(todayMark.at)} · ещё один голос</span>
          </div>
          <button type="button" className="mark-done__undo" onClick={onUndo}>
            Отменить
          </button>
        </div>
      ) : (
        <div className="mark-buttons">
          {/* При двух пропусках роли меняются: «2 минуты» становится главной. */}
          <button
            type="button"
            className={`mark-button t-button mark-button--${twoMisses ? 'secondary' : 'primary'}`}
            onClick={() => onMark?.('full')}
          >
            Сделал
          </button>
          <button
            type="button"
            className={`mark-button t-button mark-button--${twoMisses ? 'primary' : 'secondary'}`}
            onClick={() => onMark?.('mini')}
          >
            Хотя бы 2 минуты
          </button>
        </div>
      )}
    </article>
  );
}

interface PausedCardProps {
  habit: Habit;
  votes: number;
  /** «Со 2 октября» — начало паузы, вместе с предлогом. */
  pausedLabel: string;
  onResume: () => void;
}

export function PausedCard({ habit, votes, pausedLabel, onResume }: PausedCardProps) {
  return (
    <article className="paused-card">
      <div className="paused-card__text">
        <div className="habit-card__head">
          <h3 className="t-identity">
            <Link className="habit-card__link" to={`/habit/${habit.id}`}>
              Я человек, который {habit.identity}
            </Link>
          </h3>
          <EditLink habitId={habit.id} />
        </div>
        <p className="paused-card__meta">
          {pausedLabel}. {votesWord(votes)} и серия сохранены
        </p>
      </div>
      <button type="button" className="paused-card__btn t-button" onClick={onResume}>
        Вернуть
      </button>
    </article>
  );
}

/** Кнопка «Изменить» — карандаш 20px, линейный, как иконка баннера (04-components.md); ведёт на экран привычки. */
function EditLink({ habitId }: { habitId: string }) {
  return (
    <Link className="edit-link" to={`/habit/${habitId}`} aria-label="Изменить привычку">
      <svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true">
        <path
          d="M12.6 4.1 15.9 7.4M3.5 16.5l.7-3.6 9.3-9.3a1.6 1.6 0 0 1 2.3 0l1 1a1.6 1.6 0 0 1 0 2.3l-9.3 9.3-3.6.7Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </Link>
  );
}
