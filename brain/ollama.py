"""Клиент Ollama /api/chat с fallback-заглушками."""
import random
import aiohttp

import config
from brain.persona import build_system
from brain import cloud as cloud_backend
from brain import memory

FALLBACKS = [
    "Олламушка сдох, а ты всё равно долбоёб 🤣 Запусти ollama serve, еблан, потом поговорим.",
    "Бля, мозги отвалились (Ollama не отвечает). Но даже без мозгов я умнее тебя, мудила.",
    "Э, шнырь, подними Ollama: `ollama serve` + `ollama pull {model}`. Без меня ты никто.",
    "Пиздец, сервер молчит. Ты его тоже заебал, походу 💩",
]

ROAST_FALLBACKS = [
    "Ты такой страшный, что когда гуглишь свой фотопортрет — антивирус орёт, {name} 🤣",
    "Твой IQ как wifi в лифте — вроде есть, а нихуя не ловит, {name} 💩",
    "Ты не тупой, ты просто эксклюзивный долбоёб, лимитированная серия, {name} 🔥",
    "Тебя в детстве роняли, но судя по всему — целились, {name} 🤣",
]


def _headers() -> dict:
    """Bearer для прямого Cloud API (https://ollama.com). Локалке заголовок не нужен."""
    if config.OLLAMA_API_KEY:
        return {"Authorization": f"Bearer {config.OLLAMA_API_KEY}"}
    return {}


def _model() -> str:
    """Прямой Cloud API хочет имена без суффикса -cloud, локальный демон — с ним."""
    m = config.OLLAMA_MODEL
    if config.OLLAMA_API_KEY and "ollama.com" in config.OLLAMA_URL and m.endswith("-cloud"):
        return m[: -len("-cloud")]
    return m


async def chat(chat_id: int, user_text: str, user_name: str = "чел", mode: str = None, extra_system: str = "") -> str:
    """Главный вызов: память + persona + Ollama."""
    mode = mode or config.HAM_MODE
    system = build_system(mode)
    if extra_system:
        system += "\n" + extra_system

    memory.add(chat_id, "user", f"{user_name}: {user_text}")
    messages = [{"role": "system", "content": system}]
    messages += memory.get(chat_id)[-config.MEMORY_LEN:]

    # 1. облако (быстро)
    cloud_ans = await cloud_backend.chat(messages)
    if cloud_ans:
        memory.add(chat_id, "assistant", cloud_ans)
        return cloud_ans

    # 2. локальная Ollama (fallback)
    async def _ask(msgs):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.OLLAMA_TIMEOUT)) as s:
            payload = {
                "model": _model(),
                "messages": msgs,
                "stream": False,
                "keep_alive": "1h",
                "options": {"temperature": config.OLLAMA_TEMP, "num_predict": 120, "num_ctx": 32768, "repeat_penalty": 1.15},
            }
            async with s.post(f"{config.OLLAMA_URL}/api/chat", json=payload, headers=_headers()) as r:
                if r.status != 200:
                    txt = await r.text()
                    raise RuntimeError(f"Ollama {r.status}: {txt[:300]}")
                data = await r.json()
                answer = (data.get("message", {}).get("content") or "").strip()
                if not answer:
                    raise RuntimeError("пустой ответ")
                return answer

    try:
        try:
            answer = await _ask(messages)
        except Exception:
            # контекст не влез — пробуем с короткой историей
            trimmed = [messages[0]] + [mm for mm in messages[1:] if mm.get("role") != "system"][-15:]
            answer = await _ask(trimmed)
        memory.add(chat_id, "assistant", answer)
        return answer
    except Exception:
        ans = random.choice(FALLBACKS).format(model=config.OLLAMA_MODEL)
        # не кладём fallback в память чтобы не портить контекст
        return ans


async def one_shot(prompt: str, mode: str = None) -> str:
    """Разовый запрос без памяти (для roast/клички/проактива)."""
    mode = mode or config.HAM_MODE
    system = build_system(mode)

    cloud_ans = await cloud_backend.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        max_tokens=250,
    )
    if cloud_ans:
        return cloud_ans

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.OLLAMA_TIMEOUT)) as s:
            payload = {
                "model": _model(),
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "keep_alive": "1h",
                "options": {"temperature": 1.0, "num_predict": 200, "num_ctx": 4096, "repeat_penalty": 1.15},
            }
            async with s.post(f"{config.OLLAMA_URL}/api/chat", json=payload, headers=_headers()) as r:
                data = await r.json()
                return (data.get("message", {}).get("content") or "").strip() or "Чё-то я подвис, повтори, еблан."
    except Exception:
        return random.choice(FALLBACKS).format(model=config.OLLAMA_MODEL)


async def check_ollama() -> tuple[bool, str]:
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(f"{config.OLLAMA_URL}/api/tags", headers=_headers()) as r:
                if r.status != 200:
                    return False, f"HTTP {r.status}"
                data = await r.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                if _model() not in models and models:
                    return True, f"работает, но модели {_model()} нет. Есть: {', '.join(models)}. Сделай: ollama pull {_model()}"
                if not models:
                    return False, f"моделей нет вообще. Сделай: ollama pull {_model()}"
                return True, f"OK, модель {_model()} на месте"
    except Exception as e:
        return False, f"не отвечает: {e}. Запусти: ollama serve"


async def vision(chat_id: int, image_b64: str, caption: str = "", user_name: str = "чел", mode: str = None) -> str | None:
    """Разбор фото. Возвращает текст или None (модель не умеет в картинки / ошибка)."""
    mode = mode or config.HAM_MODE
    system = build_system(mode)
    system += "\nТебе скинули ФОТО. Разнеси что на нём жёстко, коротко, с матом. Если есть подпись — ответь и на неё."

    memory.add(chat_id, "user", f"{user_name}: [фото]{(' ' + caption) if caption else ''}")
    messages = [{"role": "system", "content": system}]
    messages += memory.get(chat_id)[-6:]
    messages.append({
        "role": "user",
        "content": caption or "Чё скажешь?",
        "images": [image_b64],
    })

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.OLLAMA_TIMEOUT)) as s:
            payload = {
                "model": _model(),
                "messages": messages,
                "stream": False,
                "keep_alive": "1h",
                "options": {"temperature": config.OLLAMA_TEMP, "num_predict": 150, "num_ctx": 4096, "repeat_penalty": 1.15},
            }
            async with s.post(f"{config.OLLAMA_URL}/api/chat", json=payload, headers=_headers()) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                answer = (data.get("message", {}).get("content") or "").strip()
                if not answer:
                    return None
                memory.add(chat_id, "assistant", answer)
                return answer
    except Exception:
        return None
