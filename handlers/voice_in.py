"""Входящие голосовые/аудио/кружки: распознаём (faster-whisper) и отвечаем как на текст."""
import asyncio
import io
import logging
import os
import uuid

from aiogram import Router, F
from aiogram.types import Message

from handlers.chat import answer_text

log = logging.getLogger("hamlo.stt")
router = Router()

_TMPDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stt_tmp")
_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


async def _transcribe(path: str) -> str:
    def _run():
        model = _get_model()
        segs, _info = model.transcribe(path, language="ru", beam_size=5)
        return "".join(s.text for s in segs).strip()
    return await asyncio.to_thread(_run)


@router.message(F.voice | F.audio | F.video_note)
async def voice_in(m: Message):
    src = m.voice or m.audio or m.video_note
    dur = getattr(src, "duration", 0) or 0
    if dur > 180:
        await m.answer("Охуел столько пиздеть? Режь до 3 минут, еблан.", parse_mode=None)
        return
    await m.bot.send_chat_action(m.chat.id, "typing")
    ext = ".ogg" if m.voice else (".mp3" if m.audio else ".mp4")
    path = os.path.join(_TMPDIR, f"in_{uuid.uuid4().hex}{ext}")
    try:
        os.makedirs(_TMPDIR, exist_ok=True)
        fg = await m.bot.get_file(src.file_id)
        buf = io.BytesIO()
        await m.bot.download_file(fg.file_path, buf)
        with open(path, "wb") as f:
            f.write(buf.getvalue())
        text = await _transcribe(path)
    except Exception as e:
        log.warning("STT fail: %s", e)
        await m.answer("Чё ты там пробулькал, еблан? Нихуя не понял, повтори текстом.", parse_mode=None)
        return
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
    if not text:
        await m.answer("Тишина, блять. Ты мне молчание прислал? Пиши текстом, еблан.", parse_mode=None)
        return
    await answer_text(m, f"(гс) {text}")
