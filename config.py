"""Конфиг Хамло-бота."""
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

# Ollama
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434").strip().rstrip("/")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud").strip()
OLLAMA_API_KEY: str = os.getenv("OLLAMA_API_KEY", "").strip()
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "90"))
OLLAMA_TEMP: float = float(os.getenv("OLLAMA_TEMP", "0.9"))

# Характер: всегда агро. light | zhest | max оставлены для совместимости, но все = агро
HAM_MODE: str = os.getenv("HAM_MODE", "max").strip().lower()
if HAM_MODE not in ("light", "zhest", "max"):
    HAM_MODE = "max"

# В группах отвечать ВСЕГДА (1.0) — бот постоянно агро
TRIGGER_CHANCE: float = float(os.getenv("TRIGGER_CHANCE", "1.0"))

# Проактив: бот сам пишет если чат молчит (по умолчанию ВЫКЛ - спалил)
PROACTIVE_ENABLED: bool = os.getenv("PROACTIVE_ENABLED", "false").lower() in ("1", "true", "yes", "on")
PROACTIVE_INTERVAL_MIN: int = int(os.getenv("PROACTIVE_INTERVAL_MIN", "15"))
PROACTIVE_CHANCE: float = float(os.getenv("PROACTIVE_CHANCE", "1.0"))

# Память
MEMORY_LEN: int = int(os.getenv("MEMORY_LEN", "200"))

# Облако (OpenAI-compatible). Приоритет над Ollama, при ошибке — fallback на локаль
USE_CLOUD: bool = os.getenv("USE_CLOUD", "true").lower() in ("1", "true", "yes", "on")
CLOUD_API_BASE: str = os.getenv("CLOUD_API_BASE", "https://free.sysik.mom/v1").strip().rstrip("/")
CLOUD_API_KEY: str = os.getenv("CLOUD_API_KEY", "").strip()
CLOUD_MODEL: str = os.getenv("CLOUD_MODEL", "gpt-4o-mini").strip()
CLOUD_TIMEOUT: int = int(os.getenv("CLOUD_TIMEOUT", "60"))

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    print("WARNING: BOT_TOKEN не задан. Скопируй .env.example в .env и вставь токен от @BotFather")
