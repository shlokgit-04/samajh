"""Samajh: understand your paperwork, track the process, get what you are owed.

FastAPI app factory: security middleware, exception handlers, API routers and
the static front-end.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, store
from .gemini_client import GemmaClient, NoKeysConfigured, PoolExhausted
from .routes_auth import router as auth_router
from .routes_docs import router as docs_router
from .routes_pdf import router as pdf_router
from .routes_reco import router as reco_router
from .routes_scans import router as scans_router
from .routes_tracker import router as tracker_router

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


@asynccontextmanager
async def lifespan(app):
    store.init_db()
    store.cleanup_expired_scans()
    yield


app = FastAPI(title="Samajh", docs_url=None, redoc_url=None, lifespan=lifespan)
app.state.client = GemmaClient()


@app.exception_handler(PoolExhausted)
async def pool_exhausted_handler(request, exc):
    return JSONResponse(status_code=503, content={"error": str(exc)})


@app.exception_handler(NoKeysConfigured)
async def no_keys_handler(request, exc):
    return JSONResponse(
        status_code=503,
        content={
            "error": "Reading documents needs a Gemini API key. Add GEMINI_API_KEYS in .env and restart; "
                     "everything else on the site works without it."
        },
    )


@app.exception_handler(Exception)
async def unhandled_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Something went wrong on our side. Please try again."},
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(self), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline' "
        "https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
        "form-action 'self'; frame-ancestors 'none'",
    )
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/api/health")
async def health():
    snap = app.state.client.pool.snapshot()
    key_entries = {k: config.LANG_NAMES[k] for k in config.SUPPORTED_LANGS}
    return {
        "ok": snap["total"] > 0,
        "keys": snap,
        "model": config.GEMMA_MODEL,
        "fallback_model": config.GEMMA_FALLBACK_MODEL,
        "db": "supabase" if (config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY) else "local",
        "store": "sqlite",
        "auth": True,
        "langs": key_entries,
        "roles": config.ROLE_NAMES,
        "retention_days": config.SCAN_RETENTION_DAYS,
    }


@app.get("/api/privacy")
async def privacy():
    """Plain-language privacy note, also rendered in the footer."""
    return {
        "encrypted_vault": True,
        "retention_days": config.SCAN_RETENTION_DAYS,
        "no_plaintext_documents": True,
        "no_sale_of_data": True,
        "right_to_export": "/api/auth/export",
        "right_to_erasure": "DELETE /api/auth/me",
        "notes": [
            "Passwords are hashed with bcrypt and never stored in plain text.",
            "Sessions are httpOnly, SameSite=Strict cookies.",
            "Uploaded documents are encrypted per user (Fernet, HKDF-derived keys).",
            f"Scans auto-delete after {config.SCAN_RETENTION_DAYS} days, or the moment you delete them.",
            "You can export everything or erase everything from the Account panel.",
        ],
    }


app.include_router(auth_router)
app.include_router(docs_router)
app.include_router(scans_router)
app.include_router(tracker_router)
app.include_router(reco_router)
app.include_router(pdf_router)

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
