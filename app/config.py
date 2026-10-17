"""Environment configuration for Samajh."""
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SCANS_DIR = os.path.join(DATA_DIR, "scans")
DB_PATH = os.getenv("SAMAJH_DB_PATH", "").strip() or os.path.join(DATA_DIR, "samajh.db")

GEMINI_API_KEYS = [
    k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()
]

# Gemma 4 via the Gemini API. Both are configurable so a rate-limited or
# unavailable primary can be swapped without touching code.
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")
GEMMA_FALLBACK_MODEL = os.getenv("GEMMA_FALLBACK_MODEL", "gemma-4-26b-a4b-it")

# Optional Supabase backend for the shared forms knowledge base.
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()

# Auth and encryption.
# APP_SECRET_KEY should be set in production; when missing a local key file is
# generated (data/.secret.key, owner-only permissions) so everything still works.
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "").strip()
ACCESS_TOKEN_DAYS = int(os.getenv("ACCESS_TOKEN_DAYS", "7"))
COOKIE_NAME = "samajh_session"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0").strip() == "1"

ADMIN_EMAILS = [
    e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
]

# Roles drive recommendations. citizen is the default.
SUPPORTED_ROLES = (
    "citizen",
    "farmer",
    "govt_employee",
    "doctor",
    "student",
    "senior_citizen",
    "entrepreneur",
    "worker",
)
ROLE_NAMES = {
    "citizen": "General citizen",
    "farmer": "Farmer",
    "govt_employee": "Government service employee",
    "doctor": "Doctor",
    "student": "Student",
    "senior_citizen": "Senior citizen",
    "entrepreneur": "Business owner / entrepreneur",
    "worker": "Worker (unorganised sector)",
}

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB
MAX_IMAGE_SIDE = 1600

# Scan vault.
SCAN_RETENTION_DAYS = int(os.getenv("SCAN_RETENTION_DAYS", "30"))
MAX_SCANS_PER_USER = int(os.getenv("MAX_SCANS_PER_USER", "100"))

# Simple in-memory rate limits: attempts per window (seconds).
RATE_LIMITS = {
    "auth": (30, 300),
    "analyze": (20, 300),
    "chat": (40, 300),
    "pdf": (30, 300),
}

SUPPORTED_LANGS = ("en", "hi", "mr", "ta", "te", "bn", "gu", "kn", "ml", "pa")
LANG_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
}
LANG_NATIVE = {
    "en": "English",
    "hi": "हिंदी",
    "mr": "मराठी",
    "ta": "தமிழ்",
    "te": "తెలుగు",
    "bn": "বাংলা",
    "gu": "ગુજરાતી",
    "kn": "ಕನ್ನಡ",
    "ml": "മലയാളം",
    "pa": "ਪੰਜਾਬੀ",
}
# BCP-47 locales used by the browser's text-to-speech and PDF font choice.
LANG_LOCALES = {
    "en": "en-IN",
    "hi": "hi-IN",
    "mr": "mr-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "bn": "bn-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
}
