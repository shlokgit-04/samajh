"""Shared test setup: isolated DB, secret and no Gemini keys.

Must set the environment BEFORE app.config is imported anywhere.
"""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="samajh-tests-")
os.environ.setdefault("SAMAJH_DB_PATH", os.path.join(_TMP, "test.db"))
os.environ.setdefault("APP_SECRET_KEY", "unit-test-secret-key")
os.environ["GEMINI_API_KEYS"] = ""
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_SERVICE_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import security, store  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def user_client(client):
    """A fresh registered user session with its own cookie jar."""
    store.reset_for_tests()
    with TestClient(app) as c:
        res = c.post("/api/auth/register", json={
            "email": f"user{os.urandom(4).hex()}@example.com",
            "password": "strongpassword1",
            "name": "Test User",
            "role": "farmer",
            "lang": "en",
            "area": "Pune",
            "consent": True,
        })
        assert res.status_code == 200, res.text
        yield c


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    store.reset_for_tests()
    import shutil

    shutil.rmtree(_TMP, ignore_errors=True)
