"""Тексты бота сверяем с design/09-bot.md и эталонами 8.1–8.3."""

import datetime as dt
import uuid

from app.bot import texts
from app.bot.messages import reminder_message
from app.models import Habit
from app.services.stats import compute_stats

TODAY = dt.date(2026, 10, 2)


def make(pattern: str, today_kind: str | None = None, mini: str = "одна страница"):
    """pattern — дни с начала привычки до вчера: d сделал, m две минуты, x пропуск."""
    start = TODAY - dt.timedelta(days=len(pattern))
    marks = {start + dt.timedelta(days=i): ("full" if c == "d" else "mini") for i, c in enumerate(pattern) if c != "x"}
    if today_kind:
        marks[TODAY] = today_kind
    habit = Habit(
        id=uuid.uuid4(), identity="читает", full="читаю 30 минут", mini=mini, anchor="налью утренний кофе",
        created_at=start,
    )
    return habit, compute_stats(start, marks, [], TODAY)


def test_plural():
    assert [texts.votes_word(n) for n in (1, 2, 5, 11, 21, 23)] == [
        "1 голос", "2 голоса", "5 голосов", "11 голосов", "21 голос", "23 голоса",
    ]
    assert texts.days_word(6) == "6 дней" and texts.days_word(4) == "4 дня"


def test_morning():
    habit, stats = make("ddmdxdddmdddd")
    lines = texts.morning(habit, stats).split("\n")
    assert lines == [
        "<b>Я человек, который читает</b>",
        "После того как налью утренний кофе — самое время.",
        "",
        "Полная версия: <b>читаю 30 минут</b>",
        "На две минуты: <b>одна страница</b>",
        "<blockquote>●●◐●○●●●◐●●●●◌",
        "12 голосов · серия 12 дней</blockquote>",
    ]


def test_marked_full_and_mini():
    habit, stats = make("ddmdxdddmdddd", today_kind="full")
    lines = texts.marked(habit, stats, "full").split("\n")
    assert lines[1] == "Сделал полностью — капля засчитана."
    assert lines[2].endswith("●●●●●")
    assert lines[3] == "13 голосов · серия 13 дней</blockquote>"
    assert texts.marked(habit, stats, "mini").split("\n")[1] == "Две минуты засчитаны."


def test_evening_after_yesterday_miss():
    habit, stats = make("dddx", mini="надеть кроссовки и выйти за дверь")
    text, keyboard = reminder_message(habit, stats, "evening")
    lines = text.split("\n")
    assert lines[1] == "Вчера не вышло — это нормально. Сегодня хватит и двух минут."
    assert lines[3] == "На две минуты: <b>надеть кроссовки и выйти за дверь</b>"
    # Вечером — только кнопки отметки.
    assert [[b.text for b in row] for row in keyboard.inline_keyboard] == [["Сделал", "2 минуты"]]


def test_evening_without_miss():
    habit, stats = make("dddd")
    assert texts.evening(habit, stats).split("\n")[1] == "Сегодня ещё без капли. Хватит и двух минут."


def test_two_misses_message_and_reversed_buttons(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.webapp_url", "https://example.org")
    habit, stats = make("dddxx", mini="надень кроссовки")
    text, keyboard = reminder_message(habit, stats, "morning")
    lines = text.split("\n")
    assert lines[1:] == [
        "Два дня без капли — так бывает. Голоса никуда не делись, вернись с малого.",
        "",
        "На две минуты: <b>надень кроссовки</b>",
        "<blockquote>●●●○○◌",
        "3 голоса · серия начнётся заново</blockquote>",
    ]
    assert [[b.text for b in row] for row in keyboard.inline_keyboard] == [["2 минуты", "Сделал"], ["Открыть Каплю"]]
    assert keyboard.inline_keyboard[0][0].callback_data == f"mark:{habit.id}:mini"
    # Синяя — первая кнопка, здесь это «2 минуты».
    assert [b.style for b in keyboard.inline_keyboard[0]] == ["primary", None]


def test_two_misses_without_votes():
    # Голосов ещё нет — не пишем «голоса никуда не делись».
    habit, stats = make("xx")
    lines = texts.two_misses(habit, stats).split("\n")
    assert lines[1] == "Два дня без капли — так бывает. Начни с самого малого, этого хватит."
    assert lines[-2:] == ["<blockquote>○○◌", "Первый голос — сегодня</blockquote>"]


def test_morning_full_button_is_primary():
    habit, stats = make("dddd")
    _, keyboard = reminder_message(habit, stats, "morning")
    assert [b.style for b in keyboard.inline_keyboard[0]] == ["primary", None]


def test_user_text_is_escaped():
    habit, stats = make("d")
    habit.identity = "<script>"
    assert "&lt;script&gt;" in texts.morning(habit, stats)
