# 06 · Анимация

Главный момент — **падающая капля** при отметке. Остальное движение минимальное. Живой пример — `reference/today-prototype.html` (нажми «Сделал» на второй карточке; там слой круга называется `.rip`, а ячейка — `.s-d`/`.s-m`).

## Капля (≈0.8 с)

Сегодняшняя ячейка содержит три слоя: заливку, каплю и круг.

```css
.day .drop {          /* капля 9×9, острым концом вверх */
  position: absolute; left: 50%; top: -4px; width: 9px; height: 9px; margin-left: -4.5px;
  background: var(--accent); border-radius: 0 50% 50% 50%; transform: rotate(45deg); opacity: 0;
}
.day .ripple { position: absolute; inset: -2px; border-radius: 50%; border: 1.5px solid var(--accent); opacity: 0; }

.day.just .drop   { animation: fall .46s cubic-bezier(.55,0,.9,.4) both; }
.day.just .fill   { animation: fillIn .32s .42s cubic-bezier(.2,.8,.3,1.2) both; }
.day.just .ripple { animation: ripple .7s .44s ease-out both; }

@keyframes fall   { 0% { opacity:0; transform: translateY(-34px) rotate(45deg) scale(.6) }
                    25% { opacity:1 }
                    92% { opacity:1; transform: translateY(6px) rotate(45deg) scale(1) }
                    100% { opacity:0; transform: translateY(9px) rotate(45deg) scale(.4) } }
@keyframes fillIn { from { transform: scale(.2); opacity: 0 } to { transform: scale(1); opacity: 1 } }
@keyframes ripple { from { transform: scale(.8); opacity: .7 } to { transform: scale(2.3); opacity: 0 } }
```

Последовательность: капля падает 0–0.46 с → ячейка наполняется с лёгким перелётом 0.42–0.74 с → круг расходится 0.44–1.14 с → строка MarkDone появляется (fade-up 6px, 0.35 с, задержка 0.5 с) → вода в шапке поднимается.

## Вода в шапке

`height` слоя воды меняется плавно: `transition: height .9s cubic-bezier(.3,.7,.2,1)`.

## Прочее

- Знакомство 2.1: круги наполняются по очереди, `pop .35s`, задержка `index × 60ms`.
- Пустое состояние 2.4: в первое кольцо раз в 3.6 с падает капля (те же кадры, зациклено).
- Подсказка ИИ: плейсхолдеры мерцают (сдвиг фона 1.4 с, линейно).
- Нажатие кнопки: `scale(.98)` на 100 мс.
- Нижние листы: выезд снизу 250 мс `cubic-bezier(.2,.8,.2,1)`, затемнение — fade 200 мс.

## prefers-reduced-motion

Капля и круг не показываются, ячейка и строка MarkDone появляются сразу, вода меняется без перехода, мерцание выключено.
