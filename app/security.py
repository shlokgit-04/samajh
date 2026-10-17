"""Security helpers: password hashing, JWT sessions, per-user encryption, rate limits.

Privacy design:
- Passwords are hashed with bcrypt; plaintext is never stored or logged.
- Sessions are JWTs in an httpOnly, SameSite=Strict cookie.
- Uploaded documents are encrypted at rest with Fernet, using a per-user key
  derived from the app master secret (HKDF-SHA256), so one user's vault is
  unreadable even if another user's key material leaks.
"""
import base64
import hashlib
import hmac
import os
import secrets
import threading
import time

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from . import config

JWT_ALG = "HS256"
JWT_ISSUER = "samajh"

_secret_cache = {"value": None, "lock": threading.Lock()}


def _load_or_create_secret():
    """APP_SECRET_KEY from the environment, else a generated local key file."""
    if config.APP_SECRET_KEY:
        return config.APP_SECRET_KEY.encode("utf-8")
    os.makedirs(config.DATA_DIR, exist_ok=True)
    path = os.path.join(config.DATA_DIR, ".secret.key")
    if os.path.exists(path):
        with open(path, "rb") as fh:
            return fh.read()
    key = base64.urlsafe_b64encode(secrets.token_bytes(32))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(key)
    return key


def app_secret():
    with _secret_cache["lock"]:
        if _secret_cache["value"] is None:
            _secret_cache["value"] = _load_or_create_secret()
        return _secret_cache["value"]


# ---------------------------------------------------------------- passwords

def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------- sessions

def create_token(user_id, role, days=None):
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + (days or config.ACCESS_TOKEN_DAYS) * 86400,
        "iss": JWT_ISSUER,
    }
    return jwt.encode(payload, signing_key(), algorithm=JWT_ALG)


def decode_token(token):
    """Return the payload dict, or None when the token is invalid/expired."""
    try:
        return jwt.decode(
            token, signing_key(), algorithms=[JWT_ALG], issuer=JWT_ISSUER,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        return None


# ---------------------------------------------------------------- encryption

def derive_key(info: str) -> bytes:
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info.encode("utf-8"))
    return base64.urlsafe_b64encode(hkdf.derive(app_secret()))


def signing_key() -> bytes:
    """A fixed 32-byte JWT signing key, derived so any APP_SECRET_KEY length works."""
    return derive_key("samajh:jwt")


def user_fernet(user_id: int) -> Fernet:
    """A stable per-user encryption key: a leak of one vault cannot open another."""
    return Fernet(derive_key(f"samajh:user:{int(user_id)}"))


def encrypt_for_user(user_id: int, data: bytes) -> bytes:
    return user_fernet(user_id).encrypt(data)


def decrypt_for_user(user_id: int, token: bytes) -> bytes:
    return user_fernet(user_id).decrypt(token)


def safe_decrypt(user_id: int, token: bytes, default=None):
    try:
        return decrypt_for_user(user_id, token)
    except (InvalidToken, ValueError, TypeError):
        return default


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- rate limit

class RateLimiter:
    """Thread-safe sliding-window limiter. One process, in memory, by design."""

    def __init__(self, limits):
        self.limits = limits
        self._hits = {}
        self._lock = threading.Lock()

    def allow(self, bucket, key):
        limit, window = self.limits.get(bucket, (1000, 60))
        now = time.time()
        with self._lock:
            hits = [t for t in self._hits.get((bucket, key), []) if now - t < window]
            if len(hits) >= limit:
                self._hits[(bucket, key)] = hits
                return False
            hits.append(now)
            self._hits[(bucket, key)] = hits
            return True


rate_limiter = RateLimiter(config.RATE_LIMITS)


def client_ip(request):
    """Best-effort client IP, honouring X-Forwarded-For behind a proxy."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_origin(request):
    """CSRF belt-and-braces: mutating same-site requests must carry the right Origin."""
    origin = request.headers.get("origin")
    if not origin:
        return True  # non-browser client; cookie SameSite=Strict still applies
    host = request.headers.get("host", "")
    try:
        from urllib.parse import urlparse

        return urlparse(origin).netloc == host
    except Exception:  # noqa: BLE001
        return False


def constant_time_eq(a, b):
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
