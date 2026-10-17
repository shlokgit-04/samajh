"""Gemma 4 client with a thread-safe multi-key failover pool.

Every call to the Gemini API goes through KeyPool.run(). On failure the pool
classifies the error, cools down or disables the key, and retries the same
request on the next key; if every key fails on the primary model it retries
the whole key list on the fallback model.
"""
import json
import re
import threading
import time

from google import genai
from google.genai import types

from . import config

COOLDOWN_SECONDS = 60


class PoolExhausted(Exception):
    """Every key on both models failed."""

    def __init__(self, last_error=None):
        self.last_error = last_error
        super().__init__(
            "The service is briefly overloaded. Please try again in a minute."
        )


class NoKeysConfigured(Exception):
    """GEMINI_API_KEYS is empty."""


def classify_error(exc):
    """Map an SDK/HTTP error to: rate_limit | invalid_key | server | timeout | request."""
    message = str(exc).lower()
    code = getattr(exc, "code", None)
    if isinstance(exc, TimeoutError) or "timed out" in message or "timeout" in message:
        return "timeout"
    if code == 429 or "quota" in message or "rate limit" in message or "resource_exhausted" in message:
        return "rate_limit"
    if code in (401, 403):
        return "invalid_key"
    if code == 400 and ("api key" in message or "api_key" in message or "key invalid" in message):
        return "invalid_key"
    if code is not None and code >= 500:
        return "server"
    return "server"


def extract_json(raw):
    """Best-effort JSON extraction from a model reply.

    Strips thinking blocks and code fences, then parses the outermost JSON
    object. Returns None when nothing parseable is found.
    """
    if not raw:
        return None
    text = re.sub(r"", "", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    break
    try:
        return json.loads(text[start : text.rfind("}") + 1])
    except (json.JSONDecodeError, ValueError):
        return None


class KeyPool:
    """Thread-safe pool of Gemini API keys with cooldowns and disabling."""

    def __init__(self, keys):
        self._lock = threading.Lock()
        self._keys = list(keys)
        self._cursor = 0
        self._cooldown_until = {}
        self._disabled = set()

    @property
    def total(self):
        return len(self._keys)

    def snapshot(self):
        with self._lock:
            return {
                "total": self.total,
                "active": self.total - len(self._disabled),
                "disabled": len(self._disabled),
            }

    def _order(self, ignore_cooldown=False):
        """Key indices starting at the cursor, skipping disabled and cooling keys."""
        with self._lock:
            n = len(self._keys)
            order = []
            for step in range(n):
                idx = (self._cursor + step) % n
                if idx in self._disabled:
                    continue
                if not ignore_cooldown and self._cooldown_until.get(idx, 0) > time.time():
                    continue
                order.append(idx)
            return order

    def advance(self):
        with self._lock:
            if self._keys:
                self._cursor = (self._cursor + 1) % len(self._keys)

    def note_rate_limit(self, idx):
        with self._lock:
            self._cooldown_until[idx] = time.time() + COOLDOWN_SECONDS

    def note_disabled(self, idx):
        with self._lock:
            self._disabled.add(idx)

    def run(self, request_fn):
        """Run request_fn(model, api_key) with failover across keys and models.

        Returns (result, trace) where trace names the model and key slot used.
        Raises PoolExhausted when every attempt failed.
        """
        if not self._keys:
            raise NoKeysConfigured(
                "No Gemini API keys are configured. Paste keys into GEMINI_API_KEYS in .env."
            )
        last_error = None
        models = list(dict.fromkeys([config.GEMMA_MODEL, config.GEMMA_FALLBACK_MODEL]))
        for pass_no, model in enumerate(models):
            # The fallback pass retries the WHOLE key list: cooldowns from the
            # primary model's failures do not block it (only disabled keys do).
            ignore = pass_no > 0
            for idx in self._order(ignore_cooldown=ignore):
                key = self._keys[idx]
                trace = {"model": model, "key_slot": idx, "key_last4": key[-4:]}
                try:
                    result = request_fn(model, key)
                    self.advance()
                    return result, trace
                except Exception as exc:  # noqa: BLE001 - classified below
                    last_error = exc
                    kind = classify_error(exc)
                    if kind == "rate_limit":
                        self.note_rate_limit(idx)
                        continue
                    if kind == "invalid_key":
                        self.note_disabled(idx)
                        continue
                    if kind == "timeout":
                        continue  # stalled upstream: rotate now instead of retrying the same key
                    # server / request: rotate to the next key at once. Google's
                    # free Gemma endpoint fails long prompts fast (500 INTERNAL)
                    # and is flaky per attempt, so the next key is as good a bet
                    # as a same-key retry, at half the worst-case latency.
                    continue
        raise PoolExhausted(last_error)


class GemmaClient:
    """Call layer over KeyPool: plain text, text+image, and JSON-flavoured calls."""

    def __init__(self, keys=None):
        self.pool = KeyPool(keys if keys is not None else config.GEMINI_API_KEYS)
        self._clients = {}
        self._clients_lock = threading.Lock()

    def _client(self, key):
        with self._clients_lock:
            client = self._clients.get(key)
            if client is None:
                client = genai.Client(
                    api_key=key,
                    http_options=types.HttpOptions(timeout=12 * 1000),
                )
                self._clients[key] = client
            return client

    def call(self, contents, system=None):
        """One round trip. contents: list of str and/or types.Part.

        System instructions are prepended into the user turn, because Gemma on
        the Gemini API does not accept a separate system role (confirmed by
        scripts/smoke_test.py; see the README Model notes).
        Returns (response_text, trace) with model, key slot and latency.
        """
        started = time.monotonic()

        def request_fn(model, key):
            client = self._client(key)
            payload = list(contents)
            if system:
                payload = [
                    "[INSTRUCTIONS]\n" + system + "\n\nFollow the instructions above exactly.\n"
                ] + payload
            return client.models.generate_content(model=model, contents=payload)

        # The Gemma endpoints intermittently answer 500/503 ("high demand").
        # The pool rotates keys and models; this outer pass retries the whole
        # ladder a couple of times before surfacing a friendly error.
        for attempt in range(3):
            try:
                result, trace = self.pool.run(request_fn)
                break
            except PoolExhausted:
                if attempt == 2:
                    raise
                time.sleep(3)
        text = ""
        try:
            text = result.text or ""
        except Exception:  # noqa: BLE001 - blocked or empty response
            text = ""
        trace = dict(trace)
        trace["latency_ms"] = int((time.monotonic() - started) * 1000)
        return text, trace

    def generate_json(self, contents, system=None, retries=1):
        """Call and parse JSON; retries once with a stricter instruction."""
        text, trace = self.call(contents, system=system)
        data = extract_json(text)
        attempts = 1
        while data is None and attempts <= retries:
            retry_contents = list(contents) + [
                "IMPORTANT: Your previous reply was not valid JSON. Reply again with ONLY a "
                "single valid JSON object and no other text, no markdown fences, no reasoning."
            ]
            text, trace2 = self.call(retry_contents, system=system)
            trace2["retried_parse"] = True
            trace = trace2
            data = extract_json(text)
            attempts += 1
        return data, text, trace
