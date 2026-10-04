"""Тексты сообщений бота — design/09-bot.md, эталоны screens/8.1–8.3. Формат — parse_mode HTML."""

from html import escape

from app.models import Habit
from app.services.stats import DayState, HabitStats

# Ряд дней символами: ● сделал, ◐ две минуты, · пропуск, ○ сегодня не отмечено.
# Дни до начала привычки и на паузе в ряд не попадают.
ROW_SYMBOLS: dict[DayState, str] = {"full": "●", "mini": "◐", "miss": "·", "miss2": "·", "today-empty": "○"}


def plural(n: int, one: str, few: str, many: str) -> str:
    m10, m100 = n % 10, n % 100
    if m10 == 1 and m100 != 11:
        return one
    if 2 <= m10 <= 4 and not 12 <= m100 <= 14:
        return few
    return many


def votes_word(n: int) -> str:
    return f"{n} {plural(n, 'голос', 'голоса', 'голосов')}"


def days_word(n: int) -> str:
    return f"{n} {plural(n, 'день', 'дня', 'дней')}"


def day_row(stats: HabitStats) -> str:
    return "".join(ROW_SYMBOLS[d] for d in stats.days if d in ROW_SYMBOLS)


def stats_line(stats: HabitStats) -> str:
    if stats.votes == 0:
        return "Первый голос — сегодня"
    if stats.miss_state == "two" or stats.streak == 0:
        return "серия начнётся заново"
    return f"{votes_word(stats.votes)} · серия {days_word(stats.streak)}"


def _render(habit: Habit, stats: HabitStats, line: str) -> str:
    # Ряд дней и статистика — в цитате: Telegram выделяет её полоской цвета акцента.
    return (
        f"<b>Я человек, который {escape(habit.identity)}</b>\n{line}\n"
        f"<blockquote>{day_row(stats)}\n{stats_line(stats)}</blockquote>"
    )


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def morning(habit: Habit, stats: HabitStats) -> str:
    """Утреннее напоминание: якорь как вопрос-напоминание."""
    a, f, m = escape(habit.anchor), escape(habit.full), escape(habit.mini)
    return _render(habit, stats, f"{_cap(a)}? Самое время: {f} или хотя бы {m}.")


def evening(habit: Habit, stats: HabitStats) -> str:
    """Вечернее (21:00), если за день нет отметки."""
    m = escape(habit.mini)
    if stats.miss_state == "one":
        line = f"Вчера не вышло — это нормально. Сегодня хватит двух минут: {m}."
    else:
        line = f"Сегодня ещё без капли. Хватит двух минут: {m}."
    return _render(habit, stats, line)


def two_misses(habit: Habit, stats: HabitStats) -> str:
    line = (
        f"Два дня без капли — бывает. Голоса никуда не делись: {stats.votes}. "
        f"Вернись с малого — просто {escape(habit.mini)}."
    )
    return _render(habit, stats, line)


def marked(habit: Habit, stats: HabitStats, kind: str) -> str:
    """Сообщение после нажатия «Сделал» / «2 минуты» (редактируется то же сообщение)."""
    return _render(habit, stats, "Капля засчитана — полностью." if kind == "full" else "Две минуты засчитаны.")


MARKED_TOAST = "Капля засчитана · +1 голос"

START = (
    "<b>Капля</b>\n"
    "По капле в день. Одна отметка почти ничего не меняет. Тридцать — меняют.\n"
    "Открой Каплю, чтобы завести первую привычку."
)
