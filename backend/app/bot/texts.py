"""Тексты сообщений бота — design/09-bot.md, эталоны screens/8.1–8.3. Формат — parse_mode HTML."""

from html import escape

from app.models import Habit
from app.services.stats import DayState, HabitStats

# Ряд дней символами: ● сделал, ◐ две минуты, ○ пропуск, ◌ сегодня не отмечено.
# Дни до начала привычки и на паузе в ряд не попадают.
ROW_SYMBOLS: dict[DayState, str] = {"full": "●", "mini": "◐", "miss": "○", "miss2": "○", "today-empty": "◌"}


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
        return f"{votes_word(stats.votes)} · серия начнётся заново"
    return f"{votes_word(stats.votes)} · серия {days_word(stats.streak)}"


# Полную версию и версию на две минуты пишут в любой форме: «читаю 30 минут», «одна страница»,
# «надень кроссовки». Поэтому внутрь фразы их не вставляем, а выводим строкой с подписью, как поля в приложении.
def _full_line(habit: Habit) -> str:
    return f"Полная версия: <b>{escape(habit.full)}</b>"


def _mini_line(habit: Habit) -> str:
    return f"На две минуты: <b>{escape(habit.mini)}</b>"


def _render(habit: Habit, stats: HabitStats, *lines: str) -> str:
    # Ряд дней и статистика — в цитате: Telegram выделяет её полоской цвета акцента.
    body = "\n".join(lines)
    return (
        f"<b>Я человек, который {escape(habit.identity)}</b>\n{body}\n"
        f"<blockquote>{day_row(stats)}\n{stats_line(stats)}</blockquote>"
    )


def morning(habit: Habit, stats: HabitStats) -> str:
    """Утреннее напоминание. Якорь хранится как продолжение «После того как …»."""
    anchor = f"После того как {escape(habit.anchor)} — самое время."
    return _render(habit, stats, anchor, "", _full_line(habit), _mini_line(habit))


def evening(habit: Habit, stats: HabitStats) -> str:
    """Вечернее (21:00), если за день нет отметки."""
    if stats.miss_state == "one":
        line = "Вчера не вышло — это нормально. Сегодня хватит и двух минут."
    else:
        line = "Сегодня ещё без капли. Хватит и двух минут."
    return _render(habit, stats, line, "", _mini_line(habit))


def two_misses(habit: Habit, stats: HabitStats) -> str:
    if stats.votes:
        line = "Два дня без капли — так бывает. Голоса никуда не делись, вернись с малого."
    else:
        line = "Два дня без капли — так бывает. Начни с самого малого, этого хватит."
    return _render(habit, stats, line, "", _mini_line(habit))


def marked(habit: Habit, stats: HabitStats, kind: str) -> str:
    """Сообщение после нажатия «Сделал» / «2 минуты» (редактируется то же сообщение)."""
    return _render(habit, stats, "Сделал полностью — капля засчитана." if kind == "full" else "Две минуты засчитаны.")


MARKED_TOAST = "Капля засчитана · +1 голос"
# Нажали кнопку в старом сообщении, а сегодня уже отмечено (в приложении или раньше в чате).
ALREADY_MARKED_TOAST = "Сегодня уже отмечено"

START = (
    "<b>Капля</b>\n"
    "По капле в день. Одна отметка почти ничего не меняет. Тридцать — меняют.\n"
    "Открой Каплю, чтобы завести первую привычку."
)
