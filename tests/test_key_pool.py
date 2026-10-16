"""Tests for KeyPool: rotation on 429, disabling on an invalid key, fallback model."""
import pytest

from app import config
from app.gemini_client import KeyPool, classify_error


class FakeAPIError(Exception):
    def __init__(self, code, message=""):
        self.code = code
        super().__init__(message)


def test_rotation_on_429(monkeypatch):
    monkeypatch.setattr(config, "GEMMA_MODEL", "model-a")
    monkeypatch.setattr(config, "GEMMA_FALLBACK_MODEL", "model-b")
    pool = KeyPool(["keyAAA111", "keyBBB222"])
    seen = []

    def request_fn(model, key):
        seen.append(key)
        if key == "keyAAA111":
            raise FakeAPIError(429, "Resource exhausted, quota exceeded")
        return f"ok from {key} on {model}"

    result, trace = pool.run(request_fn)
    assert result == "ok from keyBBB222 on model-a"
    assert trace["key_slot"] == 1
    # the rate-limited key is on cooldown
    assert pool._cooldown_until.get(0, 0) > 0


def test_invalid_key_is_disabled(monkeypatch):
    monkeypatch.setattr(config, "GEMMA_MODEL", "model-a")
    monkeypatch.setattr(config, "GEMMA_FALLBACK_MODEL", "model-b")
    pool = KeyPool(["bad-key-1111", "good-key-2222"])

    calls = {"n": 0}

    def request_fn(model, key):
        if key == "bad-key-1111":
            calls["n"] += 1
            raise FakeAPIError(403, "API key not valid. Please pass a valid API key.")
        return "ok"

    result, trace = pool.run(request_fn)
    assert result == "ok"
    assert 0 in pool._disabled          # disabled for the rest of the session
    assert calls["n"] == 1              # never retried


def test_fallback_model_after_all_keys_rate_limited(monkeypatch):
    monkeypatch.setattr(config, "GEMMA_MODEL", "model-a")
    monkeypatch.setattr(config, "GEMMA_FALLBACK_MODEL", "model-b")
    pool = KeyPool(["keyAAA111", "keyBBB222"])
    models_seen = []

    def request_fn(model, key):
        models_seen.append(model)
        if model == "model-a":
            raise FakeAPIError(429, "quota exceeded")
        return f"ok on {model}"

    result, trace = pool.run(request_fn)
    assert result == "ok on model-b"
    assert trace["model"] == "model-b"
    assert set(models_seen) == {"model-a", "model-b"}


def test_classify_error_buckets():
    assert classify_error(FakeAPIError(429, "quota")) == "rate_limit"
    assert classify_error(FakeAPIError(403, "forbidden")) == "invalid_key"
    assert classify_error(FakeAPIError(400, "API key not valid")) == "invalid_key"
    assert classify_error(FakeAPIError(500, "boom")) == "server"
    assert classify_error(TimeoutError("timed out")) == "timeout"
