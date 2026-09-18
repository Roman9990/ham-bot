"""Точка входа Хамло-бота (aiogram 3 + Ollama)."""
import asyncio
import logging
import sys

from aiogram import BaseMiddleware, Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, Message
from typing import Any, Awaitable, Callable, Dict

import config
from handlers import start as start_h
from handlers import photo as photo_h
from handlers import voice_in as voice_h
from handlers import chat as chat_h
from proactive import proactive_loop, touch
from brain.ollama import check_ollama
from brain.cloud import ping as cloud_ping

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("hamlo")


class TouchMiddleware(BaseMiddleware):
    """Трекинг активности для проактива. Не перехватывает хендлеры, только помечает чат."""
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            touch(event.chat.id)
            chat_h.active_chats.add(event.chat.id)
        return await handler(event, data)


async def main():
    if not config.BOT_TOKEN or ":" not in config.BOT_TOKEN:
        log.error("Нет BOT_TOKEN! Скопируй ham-bot/.env.example в ham-bot/.env и вставь токен от @BotFather")
        return

    ok, info = await check_ollama()
    if ok:
        log.info(f"Ollama: {info}")
    else:
        log.warning(f"Ollama ПРОБЛЕМА: {info} — бот запустится, но будет отвечать заглушками")

    c_ok, c_info = await cloud_ping()
    if c_ok:
        log.info(f"Cloud: {c_info}")
    else:
        log.warning(f"Cloud ПРОБЛЕМА: {c_info}")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # порядок: команды -> фан -> умный чат -> тач
    dp.include_router(start_h.router)
    dp.include_router(photo_h.router)
    dp.include_router(voice_h.router)
    dp.include_router(chat_h.router)

    # трекинг активности для проактива через middleware (не глушит команды)
    dp.message.outer_middleware(TouchMiddleware())

    await bot.set_my_commands([
        BotCommand(command="start", description="🤬 Вася"),
        BotCommand(command="help", description="❓ помощь"),
        BotCommand(command="reset", description="🧹 забыть всё"),
        BotCommand(command="status", description="⚙️ статус"),
    ])

    async def _health_server():
        # Render web service требует слушать $PORT, иначе деплой не проходит
        import os
        from aiohttp import web

        async def _ok(_request):
            return web.Response(text="vasya zhiv")

        try:
            app = web.Application()
            app.router.add_get("/", _ok)
            app.router.add_get("/healthz", _ok)
            runner = web.AppRunner(app)
            await runner.setup()
            port = int(os.getenv("PORT", "10000"))
            await web.TCPSite(runner, "0.0.0.0", port).start()
            log.info("health endpoint слушает порт %s", port)
        except Exception as e:
            log.warning("health endpoint не стартовал: %s", e)

    asyncio.create_task(proactive_loop(bot))
    asyncio.create_task(_health_server())

    log.info(f"Вася запущен! Модель {config.OLLAMA_MODEL}, режим {config.HAM_MODE}. Ctrl+C для остановки.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nВася ушёл спать, сопля.")
