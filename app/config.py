"""Environment configuration for Samajh."""
import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEYS = [
    k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()
]

# Gemma 4 via the Gemini API. Both are configurable so a rate-limited or
# unavailable primary can be swapped without touching code.
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")
GEMMA_FALLBACK_MODEL = os.getenv("GEMMA_FALLBACK_MODEL", "gemma-4-26b-a4b-it")

# Optional Supabase backend. Everything degrades gracefully without it.
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB
MAX_IMAGE_SIDE = 1600

SUPPORTED_LANGS = ("en", "hi", "mr")
LANG_NAMES = {"en": "English", "hi": "Hindi", "mr": "Marathi"}
