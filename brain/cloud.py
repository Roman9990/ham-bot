"""Облачный бэкенд: любой OpenAI-compatible API. Приоритет над локальной Ollama."""
import aiohttp

import config


async def chat(messages: list, max_tokens: int = 220) -> str | None:
    """Возвращает текст ответа или None (выключено / ошибка сети / плохой статус)."""
    if not getattr(config, "USE_CLOUD", False) or not config.CLOUD_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.CLOUD_TIMEOUT)) as s:
            payload = {
                "model": config.CLOUD_MODEL,
                "messages": messages,
                "temperature": config.OLLAMA_TEMP,
                "max_tokens": max_tokens,
            }
            headers = {"Authorization": f"Bearer {config.CLOUD_API_KEY}"}
            async with s.post(
                f"{config.CLOUD_API_BASE}/chat/completions", json=payload, headers=headers
            ) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                text = (data["choices"][0]["message"]["content"] or "").strip()
                return text or None
    except Exception:
        return None


async def ping() -> tuple:
    """Быстрая проверка облака. (ok, info)."""
    if not getattr(config, "USE_CLOUD", False):
        return False, "выключено (USE_CLOUD=false)"
    if not config.CLOUD_API_KEY:
        return False, "нет CLOUD_API_KEY"
    ans = await chat([{"role": "user", "content": "say one word: ok"}], max_tokens=5)
    if ans:
        return True, f"OK, модель {config.CLOUD_MODEL} отвечает: {ans[:60]}"
    return False, "не отвечает (сеть/ключ/баланс), будет fallback на Ollama"
