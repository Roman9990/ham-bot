"""Отправка ответа: части по /// + мемы ([sfx:]/[img:]) из живого поиска."""
import asyncio
import logging
import re

from aiogram.types import FSInputFile, Message

from brain.memes import live_img, live_sfx
from brain.voice import cleanup

log = logging.getLogger("hamlo.meme")

_SPLIT_RE = re.compile(r"\n\s*///\s*\n|\s+///\s+")
_SFX_RE = re.compile(r"\[\s*sfx\s*:\s*([^\]]{1,60})\]", flags=re.IGNORECASE)
_IMG_RE = re.compile(r"\[\s*img\s*:\s*([^\]]{1,60})\]", flags=re.IGNORECASE)


def _pop(text: str, rx):
    m = rx.search(text or "")
    val = m.group(1).strip() if m else None
    return rx.sub("", text or "").strip(), val


async def send_split(m: Message, text: str, max_parts: int = 3, user_ctx: str = ""):
    text = (text or "").strip()
    if not text:
        return
    text, sfx_val = _pop(text, _SFX_RE)
    text, img_val = _pop(text, _IMG_RE)
    parts = [p.strip() for p in _SPLIT_RE.split(text)]
    parts = [p for p in parts if p]
    if not parts:
        return
    if len(parts) > max_parts:
        parts = parts[: max_parts - 1] + [" ".join(parts[max_parts - 1 :])]
    for i, part in enumerate(parts):
        if len(part) > 3900:
            part = part[:3900] + "…"
        if i > 0:
            try:
                await m.bot.send_chat_action(m.chat.id, "typing")
            except Exception:
                pass
            await asyncio.sleep(0.7)
        await m.answer(part, parse_mode=None)

    reply_short = " ".join(parts)[:300]
    # мемы только из живого поиска в интернете, максимум один
    if img_val or sfx_val:
        log.info("meme marker: img=%s sfx=%s", img_val, sfx_val)
    if img_val:
        p = await live_img(img_val, m.chat.id, user_ctx, reply_short)
        log.info("meme img live result: %s", bool(p))
        if p:
            try:
                await m.answer_photo(FSInputFile(p))
            except Exception:
                pass
            finally:
                cleanup(p)
            return
    if sfx_val:
        ogg = await live_sfx(sfx_val, m.chat.id, user_ctx, reply_short)
        log.info("meme sfx live result: %s", bool(ogg))
        if ogg:
            try:
                await m.answer_voice(FSInputFile(ogg))
            except Exception:
                pass
            finally:
                cleanup(ogg)
