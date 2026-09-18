"""Команды /start /help /mode /reset /status."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import config
from brain import memory
from brain.ollama import check_ollama

router = Router()

MODES_DESC = {
    "light": "лайт — мягкий подъёб",
    "zhest": "жесть — стандартное хамло",
    "max": "макс — конченый блядина",
}

# юзерские режимы в памяти (chat_id -> mode)
user_modes: dict[int, str] = {}


def get_mode(chat_id: int) -> str:
    # режим всегда максимальный
    return "max"


@router.message(Command("start"))
async def start(m: Message):
    await m.answer(
        "Здорова, еблан 🤣\n"
        "Я <b>Вася</b> — матерный бот-приколист.\n\n"
        "Просто пиши мне — отвечу. Понимаю текст, голосовые и фотки.\n"
        "Память у меня огромная — всё помню, мудила.\n\n"
        "Сброс памяти: /reset\n\n"
        "Давай, не стесняйся 💩"
    )


@router.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(
        "Слушай сюда, лох:\n\n"
        "— пиши текстом, войсом или кидай фотку, всё пойму\n"
        "— мемы и войсы кидаю сам, когда в тему 🤣\n"
        "— /start — знакомство\n"
        "— /reset — забыть всё\n"
        "— /status — чё с мозгами\n\n"
        "В личке отвечаю всегда. В группе — когда реплай, тег или скучно станет."
    )


@router.message(Command("mode"))
async def mode_cmd(m: Message):
    await m.answer("Режим всегда МАКСИМУМ, переключалка для лохов отключена 💩🔥", parse_mode=None)


@router.message(Command("reset"))
async def reset_cmd(m: Message):
    memory.clear(m.chat.id)
    await m.answer("Всё забыл, как ты таблицу умножения. Давай по новой, шнырь.")


@router.message(Command("status"))
async def status_cmd(m: Message):
    ok, txt = await check_ollama()
    icon = "✅" if ok else "❌"
    await m.answer(f"{icon} Ollama: {txt}\nМодель: <code>{config.OLLAMA_MODEL}</code>\nРежим: <b>{get_mode(m.chat.id)}</b>")
