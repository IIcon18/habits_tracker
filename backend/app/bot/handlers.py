import datetime as dt
import uuid

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.core.database import SessionLocal
from app.core.exceptions import DomainError, InvalidInput
from app.core.security import TelegramUser
from app.services.users import sync_user

from . import actions, keyboards, texts

router = Router()


@router.message(CommandStart())
async def start(message: Message) -> None:
    if message.from_user is None:
        return
    async with SessionLocal() as session:
        user = await sync_user(
            session,
            TelegramUser(
                id=message.from_user.id,
                first_name=message.from_user.first_name,
                username=message.from_user.username,
                language_code=message.from_user.language_code,
            ),
            timezone=None,
        )
        # Человек сам написал боту — теперь бот может ему писать.
        user.allows_write = True
        await session.commit()
    await message.answer(texts.START, reply_markup=keyboards.start_keyboard())


async def _edit(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup) -> None:
    if not isinstance(callback.message, Message):
        return
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        # Двойное нажатие: сообщение уже в нужном виде.
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.startswith("mark:"))
async def on_mark(callback: CallbackQuery) -> None:
    _, habit_id, kind = callback.data.split(":")
    if kind not in ("full", "mini"):
        await callback.answer()
        return
    try:
        async with SessionLocal() as session:
            text, markup, toast = await actions.mark(session, callback.from_user.id, uuid.UUID(habit_id), kind)
    except DomainError as e:
        await callback.answer(e.message)
        return
    await _edit(callback, text, markup)
    await callback.answer(toast)


@router.callback_query(F.data.startswith("undo:"))
async def on_undo(callback: CallbackQuery) -> None:
    _, habit_id, day = callback.data.split(":")
    try:
        async with SessionLocal() as session:
            text, markup = await actions.undo(
                session, callback.from_user.id, uuid.UUID(habit_id), dt.date.fromisoformat(day)
            )
    except DomainError as e:
        await callback.answer(e.message)
        # Вчерашнюю отметку отменить уже нельзя — убираем кнопку «Отменить», чтобы не висела.
        if isinstance(e, InvalidInput) and isinstance(callback.message, Message):
            await callback.message.edit_reply_markup(reply_markup=keyboards.start_keyboard())
        return
    await _edit(callback, text, markup)
    await callback.answer()
