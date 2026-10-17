"""Knowledge base loading (Supabase with a silent local fallback) and usage logging.

forms.json may optionally live in Supabase; schemes.json and centres.json are
local files. Everything is cached for five minutes.
"""
import json
import os
import threading
import time

from . import config

CACHE_TTL_SECONDS = 300
_cache = {"forms": None, "forms_ts": 0.0, "schemes": None, "centres": None, "ts": 0.0}
_lock = threading.Lock()


def _data_path(name):
    return os.path.join(config.DATA_DIR, name)


def _load_local_file(name):
    with open(_data_path(name), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _supabase():
    from supabase import create_client

    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def get_forms():
    """Forms from Supabase when configured, else data/forms.json. Cached 5 minutes."""
    now = time.time()
    with _lock:
        if _cache["forms"] and now - _cache["forms_ts"] < CACHE_TTL_SECONDS:
            return _cache["forms"]

    forms = None
    if config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
        try:
            rows = _supabase().table("forms").select("data").execute()
            if rows.data:
                forms = [row["data"] for row in rows.data]
        except Exception:  # noqa: BLE001 - silent fallback is the contract
            forms = None
    if not forms:
        forms = _load_local_file("forms.json")

    with _lock:
        _cache["forms"] = forms
        _cache["forms_ts"] = now
    return forms


def _get_json_file(name, key):
    now = time.time()
    with _lock:
        if _cache[key] and now - _cache["ts"] < CACHE_TTL_SECONDS:
            return _cache[key]
    data = _load_local_file(name)
    with _lock:
        _cache[key] = data
        _cache["ts"] = now
    return data


def get_schemes():
    """Support schemes for recommendations, from data/schemes.json."""
    return _get_json_file("schemes.json", "schemes")


def get_centres():
    """Office/centre directory, from data/centres.json."""
    return _get_json_file("centres.json", "centres")


def find_form(form_id):
    """One form from the knowledge base, or None."""
    for form in get_forms():
        if form.get("id") == form_id:
            return form
    return None


def find_scheme(scheme_id):
    """One scheme from the knowledge base, or None."""
    for scheme in get_schemes():
        if scheme.get("id") == scheme_id:
            return scheme
    return None


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
