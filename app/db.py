"""Knowledge base loading (Supabase with a silent local fallback) and usage logging."""
import json
import os
import threading
import time

from . import config

CACHE_TTL_SECONDS = 300
_cache = {"data": None, "ts": 0.0}
_lock = threading.Lock()


def _data_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "forms.json")


def _load_local():
    with open(_data_path(), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _supabase():
    from supabase import create_client

    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def get_forms():
    """Forms from Supabase when configured, else data/forms.json. Cached 5 minutes."""
    now = time.time()
    with _lock:
        if _cache["data"] and now - _cache["ts"] < CACHE_TTL_SECONDS:
            return _cache["data"]

    forms = None
    if config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
        try:
            rows = _supabase().table("forms").select("data").execute()
            if rows.data:
                forms = [row["data"] for row in rows.data]
        except Exception:  # noqa: BLE001 - silent fallback is the contract
            forms = None
    if not forms:
        forms = _load_local()

    with _lock:
        _cache.update(data=forms, ts=now)
    return forms


def log_usage(kind, doc_type=None, lang=None, model=None, key_slot=None, latency_ms=None, ok=True):
    """One usage_log row per request. Never stores images, text or personal data.

    Best effort: logging failures never break the user-facing response.
    """
    if not (config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY):
        return
    try:
        _supabase().table("usage_log").insert(
            {
                "kind": kind,
                "doc_type": doc_type,
                "lang": lang,
                "model": model,
                "key_slot": key_slot,
                "latency_ms": latency_ms,
                "ok": bool(ok),
            }
        ).execute()
    except Exception:  # noqa: BLE001
        pass
