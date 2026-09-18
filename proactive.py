"""Проактив: бот сам доебывается если чат молчит."""
import asyncio
import logging
import random
import time

import config
from brain.ollama import one_shot
from brain.persona import PROACTIVE_PROMPT

log = logging.getLogger("hamlo.proactive")

# chat_id -> last_activity timestamp
last_seen: dict[int, float] = {}


def touch(chat_id: int):
    last_seen[chat_id] = time.time()


async def proactive_loop(bot):
    if not config.PROACTIVE_ENABLED:
        log.info("Проактив выключен.")
        return
    log.info(f"Проактив включён: каждые {config.PROACTIVE_INTERVAL_MIN} мин, шанс {config.PROACTIVE_CHANCE}")
    await asyncio.sleep(60)  # дать боту стартануть
    while True:
        await asyncio.sleep(config.PROACTIVE_INTERVAL_MIN * 60)
        try:
            # импортируем тут чтобы не было цикла
            from handlers.chat import active_chats
            if not active_chats:
                continue
            for chat_id in list(active_chats):
                # молчит > интервал?
                ts = last_seen.get(chat_id, 0)
                silent_min = (time.time() - ts) / 60 if ts else 999
                if silent_min < config.PROACTIVE_INTERVAL_MIN:
                    continue
                if random.random() > config.PROACTIVE_CHANCE:
                    continue
                try:
                    text = await one_shot(PROACTIVE_PROMPT)
                    await bot.send_message(chat_id, text)
                    touch(chat_id)
                    log.info(f"Проактив в {chat_id}: {text[:80]}")
                except Exception as e:
                    log.warning(f"Не смог написать в {chat_id}: {e}")
        except Exception as e:
            log.warning(f"proactive loop error: {e}")
