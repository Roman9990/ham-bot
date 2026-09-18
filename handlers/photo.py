"""Фото: качаем, отправляем в vision-модель, отвечаем."""
import asyncio
import base64
import io

from aiogram import Router, F
from aiogram.types import Message

from brain.ollama import vision as ollama_vision
from handlers.helpers import send_split
from handlers.start import get_mode

router = Router()


@router.message(F.photo)
async def photo_reply(m: Message):
    chat_id = m.chat.id
    u = m.from_user
    name = (u.first_name if u and u.first_name else "чел")[:30]
    caption = (m.caption or "").strip()[:300]

    await m.bot.send_chat_action(m.chat.id, "upload_photo")
    try:
        fg = await m.bot.get_file(m.photo[-1].file_id)
        buf = io.BytesIO()
        await m.bot.download_file(fg.file_path, buf)
        data = buf.getvalue()
    except Exception:
        await m.answer("Фотку скачать не осилил, еблан. Кинь ещё раз.", parse_mode=None)
        return
    if not data or len(data) > 8 * 1024 * 1024:
        await m.answer("Фотка какая-то жирная, не прожую. Жми сильнее, еблан.", parse_mode=None)
        return

    await m.bot.send_chat_action(m.chat.id, "typing")

    async def _keeper():
        try:
            while True:
                await asyncio.sleep(4)
                await m.bot.send_chat_action(m.chat.id, "typing")
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    keeper = asyncio.create_task(_keeper())
    try:
        b64 = base64.b64encode(data).decode()
        ans = await ollama_vision(chat_id, b64, caption, user_name=name, mode=get_mode(chat_id))
    finally:
        keeper.cancel()
    if not ans:
        await m.answer("Нихуя не разглядел на твоей фотке, мудила. Опиши словами, еблан.", parse_mode=None)
        return
    await send_split(m, ans, user_ctx=caption or "фото")
