import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import MenuButtonWebApp, WebAppInfo

from app.core.config import settings
from app.core.database import SessionLocal

from .handlers import router
from .scheduler import run_scheduler

log = logging.getLogger("app.bot")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not settings.bot_token:
        # Код 0: без токена перезапускать бесполезно (в compose restart: on-failure).
        log.error("BOT_TOKEN не задан — заполни .env и перезапусти: docker compose up -d bot")
        return

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    if settings.webapp_url:
        # Кнопка меню «Капля» открывает Mini App — в BotFather настраивать не нужно.
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Капля", web_app=WebAppInfo(url=settings.webapp_url))
        )
        log.info("кнопка меню → %s", settings.webapp_url)
    else:
        log.warning("WEBAPP_URL не задан: нет кнопки меню и «Открыть Каплю»")

    scheduler = asyncio.create_task(run_scheduler(bot, SessionLocal))
    try:
        # Polling: бот сам забирает обновления, входящий адрес не нужен.
        await dp.start_polling(bot)
    finally:
        scheduler.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
