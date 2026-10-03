import { useEffect, useMemo, useRef } from 'react';
import { Navigate, useLocation, useNavigate, useParams } from 'react-router';
import { AiSuggestion } from '../components/AiSuggestion';
import { Chips, Field, PlanPreview, StepProgress } from '../components/Form';
import { HabitCard } from '../components/HabitCard';
import { todayISO } from '../lib/date';
import { computeStats } from '../lib/stats';
import { useStore, type Draft } from '../lib/store';
import { haptic } from '../lib/telegram';
import { useBackButton, useMainButton, useSecondaryButton } from '../lib/tgButtons';
import type { Habit } from '../lib/types';
import './Wizard.css';

/** Мастер создания привычки — экраны 5.1–5.4, тексты из design/08-copy.md. */

const TOTAL = 4;

const STEPS = {
  1: { title: 'Кем ты хочешь стать?', sub: 'Начни с идентичности. Каждая отметка будет голосом за этого человека.' },
  2: { title: 'Как это выглядит?', sub: 'Полная версия — на хороший день. Версия на две минуты — на любой.' },
  3: { title: 'После чего?', sub: 'Привяжи к тому, что ты уже делаешь каждый день. Так не придётся вспоминать.' },
  4: { title: 'Чем себя порадуешь?', sub: 'Необязательно. Маленькая награда сразу после помогает закрепить привычку.' },
} as const;

type Step = keyof typeof STEPS;

const IDENTITY_CHIPS = ['читает', 'двигается', 'высыпается', 'пишет', 'учит испанский'];
const ANCHOR_CHIPS = ['проснусь', 'почищу зубы', 'налью утренний кофе', 'сяду в метро', 'закрою ноутбук'];
const REWARD_CHIPS = ['любимый чай', 'серия сериала', 'кусочек шоколада'];

/** Заполнен ли шаг (шаг 4 — необязательный). */
function stepDone(step: Step, d: Draft): boolean {
  switch (step) {
    case 1:
      return Boolean(d.identity.trim());
    case 2:
      return Boolean(d.full.trim() && d.mini.trim());
    case 3:
      return Boolean(d.anchor.trim());
    case 4:
      return true;
  }
}

export function Wizard() {
  const params = useParams();
  const step = Number(params.step) as Step;
  const location = useLocation();
  const navigate = useNavigate();
  const { draft, updateDraft, createFromDraft, resetDraft } = useStore();
  const created = useRef(false);
  const reset = useRef(resetDraft);
  reset.current = resetDraft;

  // Черновик чистим, только когда мастер уже закрыт: иначе он успеет
  // перерисоваться с пустым черновиком и вернуть на шаг 1.
  useEffect(
    () => () => {
      if (created.current) reset.current();
    },
    [],
  );

  const firstIncomplete = ([1, 2, 3] as Step[]).find((s) => s < step && !stepDone(s, draft));
  const valid = step in STEPS && !firstIncomplete;

  const goNext = () => {
    haptic.selection();
    navigate(`/new/${step + 1}`);
  };
  const create = (withReward: boolean) => {
    createFromDraft(withReward);
    created.current = true;
    haptic.success();
    navigate('/today', { replace: true });
  };

  // На первом шаге «Назад» есть, только если пришли с другого экрана (не при первом запуске).
  const canGoBack = step > 1 || location.key !== 'default';
  useBackButton(valid && canGoBack ? () => navigate(-1) : null);
  useMainButton(
    !valid
      ? null
      : step === 4
        ? { text: 'Создать', onClick: () => create(true) }
        : { text: 'Дальше', active: stepDone(step, draft), onClick: () => stepDone(step, draft) && goNext() },
  );
  useSecondaryButton(valid && step === 4 ? { text: 'Без награды', onClick: () => create(false) } : null);

  if (!(step in STEPS)) return <Navigate to="/new/1" replace />;
  if (firstIncomplete) return <Navigate to={`/new/${firstIncomplete}`} replace />;

  const { title, sub } = STEPS[step];

  return (
    <main className="wizard">
      <StepProgress step={step} total={TOTAL} />
      <h1 className="wizard__title t-screen">{title}</h1>
      <p className="wizard__sub t-body">{sub}</p>

      <div className="wizard__body">
        {step === 1 && (
          <>
            <Field
              display
              prefix="Я человек, который"
              value={draft.identity}
              onChange={(identity) => updateDraft({ identity })}
            />
            <Chips options={IDENTITY_CHIPS} value={draft.identity} onPick={(identity) => updateDraft({ identity })} />
          </>
        )}

        {step === 2 && (
          <>
            <Field label="Полная версия" value={draft.full} onChange={(full) => updateDraft({ full })} />
            <Field
              label="На две минуты"
              placeholder="Что получится даже в плохой день?"
              value={draft.mini}
              onChange={(mini) => updateDraft({ mini })}
            />
            <AiSuggestion full={draft.full} value={draft.mini} onPick={(mini) => updateDraft({ mini })} />
          </>
        )}

        {step === 3 && (
          <>
            <Field
              prefix="После того как"
              ariaLabel="После того как"
              value={draft.anchor}
              onChange={(anchor) => updateDraft({ anchor })}
            />
            <Chips options={ANCHOR_CHIPS} value={draft.anchor} onPick={(anchor) => updateDraft({ anchor })} />
            {draft.anchor.trim() && <PlanPreview anchor={draft.anchor} full={draft.full} mini={draft.mini} />}
          </>
        )}

        {step === 4 && (
          <>
            <Field
              ariaLabel="Награда"
              placeholder="Например, чашка любимого чая"
              value={draft.reward}
              onChange={(reward) => updateDraft({ reward })}
            />
            <Chips options={REWARD_CHIPS} value={draft.reward} onPick={(reward) => updateDraft({ reward })} />
            <h2 className="wizard__preview-label">Так будет выглядеть</h2>
            <DraftPreview draft={draft} />
          </>
        )}
      </div>
    </main>
  );
}

/** Карточка будущей привычки в состоянии «новая». */
function DraftPreview({ draft }: { draft: Draft }) {
  const today = todayISO();
  const habit = useMemo<Habit>(
    () => ({ id: 'draft', ...draft, status: 'active', createdAt: today }),
    [draft, today],
  );
  const stats = useMemo(() => computeStats(habit, [], today), [habit, today]);
  return <HabitCard habit={habit} stats={stats} justMarked={false} preview />;
}
