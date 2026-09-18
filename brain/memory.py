"""Память диалога по чатам."""
from collections import defaultdict, deque
from typing import Deque, Dict, List

import config

_store: Dict[int, Deque[dict]] = defaultdict(lambda: deque(maxlen=config.MEMORY_LEN))


def add(chat_id: int, role: str, content: str):
    content = (content or "").strip()[:2000]
    if not content:
        return
    _store[chat_id].append({"role": role, "content": content})


def get(chat_id: int) -> List[dict]:
    return list(_store[chat_id])


def clear(chat_id: int):
    _store[chat_id].clear()


def history_text(chat_id: int) -> str:
    return "\n".join(f"{m['role']}: {m['content']}" for m in get(chat_id))
