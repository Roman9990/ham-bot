"""Голосовые мемы из интернета: поиск звука + конверт в ogg-войс."""
import asyncio
import logging
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid

log = logging.getLogger("hamlo.voice")

_TMPDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "voice_tmp")
_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}
_SEARCH_URL = "https://www.myinstants.com/search/?"
_MEDIA_BASE = "https://www.myinstants.com"
_PLAY_RE = re.compile(r"play\('(/media/sounds/[^']+\.mp3)'")
_SFX_RE = re.compile(r"\[\s*sfx\s*:\s*([^\]]{1,60})\]", flags=re.IGNORECASE)

_last_url: dict = {}


def strip_sfx(text: str):
    """Убирает [sfx: запрос], возвращает (чистый текст, запрос|None)."""
    m = _SFX_RE.search(text or "")
    query = m.group(1).strip() if m else None
    clean = _SFX_RE.sub("", text or "").strip()
    return clean, query


def _http_get(url: str, timeout: int = 20):
    """Синхронный GET через urllib (aiohttp сайт блочит). Возвращает (статус, байты)."""
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        log.warning("http fail %s: %s", url[:80], e)
        return 0, b""


def _search_sync(query: str):
    params = urllib.parse.urlencode({"name": query})
    status, data = _http_get(_SEARCH_URL + params)
    if status != 200 or not data:
        return []
    html = data.decode("utf-8", errors="replace")
    out = []
    for path in _PLAY_RE.findall(html):
        url = _MEDIA_BASE + path
        if all(url != u for _, u in out):
            title = path.split("/")[-1].rsplit(".", 1)[0].replace("_", " ")[:60]
            out.append((title, url))
    return out


async def fetch_sfx(query: str, chat_id: int = 0, pick_url: str | None = None):
    """Ищет звук, качает, режет до 15с, конвертит в ogg. Путь или None."""
    query = (query or "").strip()[:60]
    if not query and not pick_url:
        return None
    if pick_url:
        url = pick_url
    else:
        results = await asyncio.to_thread(_search_sync, query)
        if not results:
            return None
        last = _last_url.get(chat_id)
        pick = next(((t, u) for t, u in results if u != last), results[0])
        _title, url = pick
    os.makedirs(_TMPDIR, exist_ok=True)
    base = os.path.join(_TMPDIR, f"s_{uuid.uuid4().hex}")
    mp3 = base + ".mp3"
    ogg = base + ".ogg"
    try:
        status, data = await asyncio.to_thread(_http_get, url, 25)
        if status != 200 or not data or len(data) > 3 * 1024 * 1024:
            return None
        with open(mp3, "wb") as f:
            f.write(data)
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            return None
        proc = await asyncio.to_thread(
            subprocess.run,
            [exe, "-y", "-loglevel", "error", "-i", mp3,
             "-t", "15", "-c:a", "libopus", "-b:a", "64k", ogg],
            capture_output=True,
        )
        if proc.returncode != 0 or not os.path.exists(ogg):
            return None
        _last_url[chat_id] = url
        return ogg
    except Exception as e:
        log.warning("sfx fetch fail: %s", e)
        return None
    finally:
        try:
            if os.path.exists(mp3):
                os.remove(mp3)
        except Exception:
            pass


def cleanup(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
