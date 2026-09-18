"""Главный умный чат: отвечает на всё через Ollama + триггеры."""
import asyncio
import random
import re
from aiogram import Router, F
from aiogram.types import Message

import config
from brain import memory
from brain.ollama import chat as ollama_chat
from brain.persona import TRIGGER_REPLIES
from handlers.helpers import send_split
from handlers.start import get_mode

router = Router()

# чаты где была активность — для проактива
active_chats: set[int] = set()

HELLO_WORDS = ("привет", "здравствуй", "здарова", "йо", "салют", "добрый", "hello", "hi")
TRIGGER_WORDS = (
    "хамло", "бот", "дурак", "дебил", "лох", "чмо",
    "как дела", "кто ты", "скучно", "пошёл", "пошел",
    "анекдот", "roast", "разнеси",
)


def display_name(m: Message) -> str:
    u = m.from_user
    return (u.first_name if u and u.first_name else "чел")[:30]


def is_group(m: Message) -> bool:
    return m.chat.type in ("group", "supergroup")


def bot_mentioned(m: Message) -> bool:
    if m.reply_to_message and m.reply_to_message.from_user and m.reply_to_message.from_user.is_bot:
        return True
    txt = (m.text or "").lower()
    if "хамло" in txt or "@" in txt and "ham" in txt:
        return True
    entities = m.entities or []
    for e in entities:
        if e.type in ("mention", "bot_command"):
            return True
    return False


@router.message(F.text)
async def smart_reply(m: Message):
    text = (m.text or "").strip()
    if not text:
        return
    if text.startswith("/"):
        text = text[1:].strip()
        if not text:
            return
    await answer_text(m, text)


async def answer_text(m: Message, text: str):
    chat_id = m.chat.id
    name = display_name(m)
    low = text.lower()
    active_chats.add(chat_id)

    # 1. быстрые триггеры без ИИ (чтобы был шустрый)
    # короткие слова-паразиты отдаём ИИ — иначе отвечает невпопад
    _SKIP_TRIGGERS = {"да", "нет", "ок", "окей", "ага", "угу", "понял", "понятно"}
    for key, tpl in TRIGGER_REPLIES.items():
        if key in _SKIP_TRIGGERS:
            continue
        if len(text) < 60 and re.search(r"(?<!\w)" + re.escape(key) + r"(?!\w)", low):
            # иногда всё равно идём в ИИ для разнообразия
            if random.random() < 0.35:
                break
            variants = tpl if isinstance(tpl, list) else [tpl]
            # не повторяем прошлый ответ подряд
            hist = memory.get(chat_id)
            last = hist[-1]["content"] if hist and hist[-1]["role"] == "assistant" else None
            opts = [v for v in variants if v.format(name=name) != last] or variants
            out = random.choice(opts).format(name=name)
            await m.answer(out)
            memory.add(chat_id, "user", f"{name}: {text}")
            memory.add(chat_id, "assistant", out)
            return

    # 2. в группах — фильтруем чтобы не спамил
    if is_group(m):
        mentioned = bot_mentioned(m)
        has_trigger = any(w in low for w in TRIGGER_WORDS)
        lucky = random.random() < config.TRIGGER_CHANCE
        # короткие "привет" в группе тоже цепляем
        is_hello = any(low.startswith(w) for w in HELLO_WORDS) and len(text) < 30
        if not (mentioned or has_trigger or lucky or is_hello):
            # молча запоминаем контекст, но не отвечаем
            memory.add(chat_id, "user", f"{name}: {text}")
            return

    # 3. умный ответ через Ollama (держим "печатает..." пока думает)
    await m.bot.send_chat_action(m.chat.id, "typing")

    async def _typing_keeper():
        try:
            while True:
                await asyncio.sleep(4)
                await m.bot.send_chat_action(m.chat.id, "typing")
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    keeper = asyncio.create_task(_typing_keeper())
    try:
        answer = await ollama_chat(chat_id, text, user_name=name, mode=get_mode(chat_id))
    finally:
        keeper.cancel()
    # телега лимит 4096, разбивка на части по /// — в send_split
    await send_split(m, answer, user_ctx=text)
