"""Каталог мемов + живой поиск (картинки DDG, звуки myinstants) с ИИ-судьёй."""
import asyncio
import json
import logging
import os
import re

log = logging.getLogger("hamlo.memes")

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CAT = {"sfx": {}, "img": {}}


def _load():
    global _CAT
    try:
        with open(os.path.join(_BASE, "memes", "catalog.json"), encoding="utf-8") as f:
            d = json.load(f)
            _CAT = {"sfx": d.get("sfx", {}), "img": d.get("img", {})}
    except Exception as e:
        log.warning("meme catalog fail: %s", e)


_load()


def catalog_size():
    return len(_CAT["sfx"]), len(_CAT["img"])


def get_sfx(sid):
    """Локальный ogg по id каталога или None."""
    sid = (sid or "").strip().lower()
    if sid not in _CAT["sfx"]:
        return None
    p = os.path.join(_BASE, "sfx", sid + ".ogg")
    return p if os.path.exists(p) else None


def get_img(iid):
    """Локальная картинка по id каталога или None."""
    iid = (iid or "").strip().lower()
    it = _CAT["img"].get(iid)
    if not it:
        return None
    p = os.path.join(_BASE, "memes", it.get("file", ""))
    return p if os.path.exists(p) else None


_DDG_CACHE: dict = {}

_IMG_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}


async def live_img_search(query: str):
    """Живой поиск картинок (DDG). Возвращает [(title, url)]."""
    import time
    key = (query or "").strip().lower()
    hit = _DDG_CACHE.get(key)
    if hit and time.time() - hit[0] < 3600:
        return hit[1]

    def _run():
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            out = []
            with DDGS() as ddgs:
                for r in ddgs.images(query, max_results=8, safesearch="moderate", region="ru-ru"):
                    u = r.get("image") or ""
                    t = (r.get("title") or "")[:100]
                    if u and all(u != x[1] for x in out):
                        out.append((t, u))
            return out
        except Exception as e:
            log.warning("ddg img fail: %s", e)
            return []

    res = await asyncio.to_thread(_run)
    if not res:
        await asyncio.sleep(4)
        res = await asyncio.to_thread(_run)
    _DDG_CACHE[key] = (time.time(), res)
    return res


async def _llm_judge(prompt: str):
    """Быстрый вердикт облачной модели. Возвращает текст или None."""
    try:
        import aiohttp
        import config
        payload = {
            "model": config.OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 10},
        }
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
            async with s.post(config.OLLAMA_URL.rstrip("/") + "/api/chat", json=payload) as r:
                if r.status != 200:
                    return None
                d = await r.json()
                return (d.get("message", {}).get("content") or "").strip()
    except Exception:
        return None


def _parse_idx(txt, n):
    m = re.search(r"\d+", txt or "")
    if not m:
        return None
    i = int(m.group())
    return i if 0 <= i <= n else None


async def judge_pick(query: str, kind: str, titles, user_ctx: str = "", reply: str = ""):
    """ИИ выбирает лучший вариант (1-based) или None."""
    if not titles:
        return None
    lines = "\n".join(f"{i + 1}. {t or '(без названия)'}" for i, t in enumerate(titles))
    prompt = (
        f"Ситуация: пользователь написал \"{user_ctx[:200]}\". Бот отвечает \"{reply[:200]}\".\n"
        f"Запрос для поиска мема: \"{query}\".\nНайденные варианты {kind}:\n{lines}\n"
        f"Какой вариант ТОЧНО подходит как мем-реакция под эту ситуацию? Ответь ТОЛЬКО цифрой 1-{len(titles)}. "
        f"Выбирай самый узнаваемый, хитовый и смешной вариант. Для звуков предпочитай мемы со словами (цитаты, фразы, приколы голосом), а не простые эффекты. Если ничего точно не подходит — отвечай 0. Не выбирай 'самое близкое из плохого'."
    )
    return _parse_idx(await _llm_judge(prompt), len(titles))


def _dl_img(url: str):
    """Качает картинку (jpg/png/webp, до 5МБ). Возвращает путь или None."""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers=_IMG_UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            if r.status != 200:
                return None
            data = r.read(5 * 1024 * 1024 + 1)
        if not data or len(data) > 5 * 1024 * 1024:
            return None
        if data[:2] == b"\xff\xd8":
            ext = ".jpg"
        elif data[:8] == b"\x89PNG\r\n\x1a\n":
            ext = ".png"
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            ext = ".webp"
        else:
            return None
        import uuid
        d = os.path.join(_BASE, "memes")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"live_{uuid.uuid4().hex}{ext}")
        with open(p, "wb") as f:
            f.write(data)
        return p
    except Exception:
        return None


_SENT_FILE = os.path.join(_BASE, "memes", "sent.json")
_SENT: dict = {}


def _load_sent():
    global _SENT
    try:
        from collections import deque
        with open(_SENT_FILE, encoding="utf-8") as f:
            d = json.load(f)
        for k, v in d.items():
            cid, kind = k.split("|", 1)
            _SENT[(int(cid), kind)] = deque(v[-15:], maxlen=15)
    except Exception:
        pass


def _save_sent():
    try:
        d = {f"{cid}|{kind}": list(dq) for (cid, kind), dq in _SENT.items()}
        with open(_SENT_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
    except Exception:
        pass


def _seen_urls(chat_id: int, kind: str):
    return _SENT.get((chat_id, kind), ())


def _remember(chat_id: int, kind: str, url: str):
    from collections import deque
    dq = _SENT.setdefault((chat_id, kind), deque(maxlen=15))
    if url not in dq:
        dq.append(url)
        _save_sent()


_load_sent()


async def live_img(query: str, chat_id: int = 0, user_ctx: str = "", reply: str = ""):
    """Живой поиск картинки с выбором судьи. Путь или None."""
    import urllib.parse

    junk = ("shutterstock.", "alamy.", "dreamstime.", "gettyimages.", "istockphoto.",
            "123rf.", "depositphotos.", "fotolia.", "bigstockphoto.", "canstockphoto.", "adobestock.")
    good = ("imgflip.", "redd.it", "kym-cdn.", "imgur.", "pinimg.", "joyreactor.",
            "pikabu.", "ifunny.", "9gag.", "memedroid.", "memegenerator.", "cheezburger.")

    def _rank(url: str) -> int:
        h = urllib.parse.urlparse(url).netloc.lower()
        if any(j in h for j in junk):
            return 2
        if any(g in h for g in good):
            return 0
        return 1

    cands = await live_img_search(query)
    cands = [(t, u) for t, u in cands if u and u not in _seen_urls(chat_id, "img")]
    log.info("meme img search %s: %d fresh cands", query, len(cands))
    if not cands:
        log.info("meme img: all seen, skip")
        return None
    cands.sort(key=lambda x: _rank(x[1]))
    idx = await judge_pick(query, "картинки", [t for t, _ in cands], user_ctx, reply)
    log.info("meme img judge: %s", idx)
    if idx == 0:
        log.info("meme img: judge veto, skip")
        return None
    order = []
    if idx:
        order.append(idx - 1)
    order += [i for i in range(len(cands)) if i not in order][:3]
    for i in order[:4]:
        p = await asyncio.to_thread(_dl_img, cands[i][1])
        if p:
            _remember(chat_id, "img", cands[i][1])
            log.info("meme img sent pick #%d", i + 1)
            return p
    log.info("meme img: all downloads failed")
    return None


async def live_sfx(query: str, chat_id: int = 0, user_ctx: str = "", reply: str = ""):
    """Живой поиск звука с выбором судьи. Путь к ogg или None."""
    from brain.voice import _search_sync, fetch_sfx
    tried = [query] + sorted(set((query or "").split()), key=len, reverse=True)
    results = []
    for q in tried:
        if not q:
            continue
        results = await asyncio.to_thread(_search_sync, q)
        if results:
            if q != query:
                log.info("meme sfx fallback query: %s", q)
            break
    log.info("meme sfx search %s: %d results", query, len(results))
    if not results:
        return None
    fresh = [(t, u) for t, u in results if u not in _seen_urls(chat_id, "sfx")]
    if not fresh:
        log.info("meme sfx: all seen, skip")
        return None

    def _bias(t: str) -> int:
        tl = t.lower()
        s = 0
        if any(w in tl for w in ("quote", "vine", "meme", "says", "saying", "voice",
                                 "talking", "movie", "film", "gta", "game", "anime",
                                 "cartoon", "tiktok", "цитата", "фраза", "мем", "говорит",
                                 "голос", "кино", "фильм", "игра", "аниме", "мульт",
                                 "смех", "аплодисменты")):
            s += 2
        if any(w in tl for w in ("sound effect", "sfx", "fart", "boing", "airhorn",
                                 "air horn", "explosion", "gunshot", "siren", "alarm", "beep")):
            s -= 2
        return s

    fresh.sort(key=lambda x: -_bias(x[0]))
    titles = [t for t, _ in fresh[:12]]
    idx = await judge_pick(query, "звука", titles, user_ctx, reply)
    log.info("meme sfx judge: %s", idx)
    if idx == 0:
        log.info("meme sfx: judge veto, skip")
        return None
    if idx:
        url = fresh[idx - 1][1]
        p = await fetch_sfx(query, chat_id, pick_url=url)
        if p:
            _remember(chat_id, "sfx", url)
            log.info("meme sfx sent pick #%d: %s", idx, fresh[idx - 1][0][:80])
            return p
    url0 = fresh[0][1]
    p = await fetch_sfx(query, chat_id, pick_url=url0)
    if p:
        _remember(chat_id, "sfx", url0)
    log.info("meme sfx fallback top1: %s %s", bool(p), fresh[0][0][:80])
    return p
