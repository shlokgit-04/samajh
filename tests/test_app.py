"""End-to-end API tests: auth, encrypted vault, tracker, recommendations, PDFs."""
import io
import json
import sqlite3

from PIL import Image

from app import config


def make_jpeg(color=(200, 30, 30)):
    img = Image.new("RGB", (640, 480), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


# ---------------------------------------------------------------- health

def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["auth"] is True
    assert "langs" in data and len(data["langs"]) == 10
    assert data["retention_days"] >= 1


def test_index_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Samajh" in res.text


def test_privacy_note_public(client):
    res = client.get("/api/privacy")
    assert res.status_code == 200
    assert res.json()["encrypted_vault"] is True


# ---------------------------------------------------------------- auth

def test_register_login_me_flow(client):
    email = "flow@example.com"
    res = client.post("/api/auth/register", json={
        "email": email, "password": "strongpassword1", "name": "Asha",
        "role": "doctor", "lang": "hi", "area": "Delhi", "consent": True,
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["user"]["email"] == email
    assert body["user"]["role"] == "doctor"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email

    # duplicate registration is rejected
    dup = client.post("/api/auth/register", json={
        "email": email, "password": "strongpassword1", "name": "Asha",
        "role": "doctor", "lang": "hi", "consent": True,
    })
    assert dup.status_code == 409

    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401

    bad = client.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
    assert bad.status_code == 401
    good = client.post("/api/auth/login", json={"email": email, "password": "strongpassword1"})
    assert good.status_code == 200
    client.post("/api/auth/logout")


def test_register_validation(client):
    res = client.post("/api/auth/register", json={
        "email": "not-an-email", "password": "strongpassword1", "name": "X",
        "role": "citizen", "lang": "en", "consent": True,
    })
    assert res.status_code == 400
    res = client.post("/api/auth/register", json={
        "email": "ok@example.com", "password": "short", "name": "X",
        "role": "citizen", "lang": "en", "consent": True,
    })
    assert res.status_code == 422  # pydantic min_length
    res = client.post("/api/auth/register", json={
        "email": "ok2@example.com", "password": "strongpassword1", "name": "X",
        "role": "citizen", "lang": "en", "consent": False,
    })
    assert res.status_code == 400


def test_protected_endpoints_401(client):
    for path in ["/api/auth/me", "/api/scans", "/api/applications", "/api/alerts", "/api/recommendations"]:
        assert client.get(path).status_code == 401, path


def test_profile_update_and_password(user_client):
    res = user_client.patch("/api/auth/me", json={"name": "Renamed", "role": "worker", "area": "Nashik"})
    assert res.status_code == 200
    assert res.json()["name"] == "Renamed"
    assert res.json()["role"] == "worker"

    bad = user_client.post("/api/auth/password", json={"current_password": "nope", "new_password": "anotherpassword1"})
    assert bad.status_code == 401
    ok = user_client.post("/api/auth/password", json={"current_password": "strongpassword1", "new_password": "anotherpassword1"})
    assert ok.status_code == 200
    relogin = user_client.post("/api/auth/login", json={
        "email": user_client.get("/api/auth/me").json()["email"],
        "password": "anotherpassword1",
    })
    assert relogin.status_code == 200


def test_export_and_delete_account(client):
    email = "erase@example.com"
    client.post("/api/auth/register", json={
        "email": email, "password": "strongpassword1", "name": "Erase",
        "role": "citizen", "lang": "en", "consent": True,
    })
    client.post("/api/scans", files={"image": ("s.jpg", make_jpeg(), "image/jpeg")}, data={"lang": "en"})
    export = client.get("/api/auth/export")
    assert export.status_code == 200
    payload = json.loads(export.text)
    assert payload["user"]["email"] == email
    assert len(payload["scans"]) == 1
    assert "password_hash" not in payload["user"]

    deleted = client.delete("/api/auth/me")
    assert deleted.status_code == 200
    assert client.get("/api/auth/me").status_code == 401


# ---------------------------------------------------------------- vault

def test_scan_vault_encrypted_at_rest(user_client):
    res = user_client.post(
        "/api/scans",
        files={"image": ("bill.jpg", make_jpeg((10, 90, 200)), "image/jpeg")},
        data={"lang": "en", "label": "Electricity bill"},
    )
    assert res.status_code == 200, res.text
    scan_id = res.json()["scan"]["id"]

    listing = user_client.get("/api/scans").json()
    assert any(s["id"] == scan_id for s in listing["scans"])
    assert listing["retention_days"] == config.SCAN_RETENTION_DAYS

    img = user_client.get(f"/api/scans/{scan_id}/image")
    assert img.status_code == 200
    assert img.headers["content-type"].startswith("image/jpeg")
    assert img.content[:2] == b"\xff\xd8"  # decoded JPEG

    download = user_client.get(f"/api/scans/{scan_id}/download")
    assert download.status_code == 200
    assert "attachment" in download.headers["content-disposition"]

    # the raw database must not contain the plaintext JPEG bytes
    conn = sqlite3.connect(config.DB_PATH)
    blob = conn.execute("SELECT blob_enc FROM scans WHERE id = ?", (scan_id,)).fetchone()[0]
    conn.close()
    assert blob[:2] != b"\xff\xd8"

    assert user_client.delete(f"/api/scans/{scan_id}").status_code == 200
    assert user_client.get(f"/api/scans/{scan_id}").status_code == 404


def test_scan_upload_rejects_non_image(user_client):
    res = user_client.post(
        "/api/scans",
        files={"image": ("notes.txt", b"this is not an image", "text/plain")},
        data={"lang": "en"},
    )
    assert res.status_code == 400
    assert "image" in res.json()["detail"].lower()


def test_scans_are_isolated_between_users(client):
    with TestClientScope(client) as a:
        a.post("/api/auth/register", json={
            "email": "alice@example.com", "password": "strongpassword1", "name": "Alice",
            "role": "citizen", "lang": "en", "consent": True,
        })
        scan_id = a.post("/api/scans", files={"image": ("x.jpg", make_jpeg(), "image/jpeg")},
                         data={"lang": "en"}).json()["scan"]["id"]
    with TestClientScope(client) as b:
        b.post("/api/auth/register", json={
            "email": "bob@example.com", "password": "strongpassword1", "name": "Bob",
            "role": "citizen", "lang": "en", "consent": True,
        })
        assert b.get(f"/api/scans/{scan_id}").status_code == 404
        assert b.delete(f"/api/scans/{scan_id}").status_code == 404


class TestClientScope:
    """Helper: a TestClient with its own cookie jar, reusing the same app."""

    __test__ = False

    def __init__(self, _):
        from fastapi.testclient import TestClient

        from app.main import app

        self._c = TestClient(app)

    def __enter__(self):
        return self._c.__enter__()

    def __exit__(self, *exc):
        return self._c.__exit__(*exc)


def test_delete_all_scans(user_client):
    for _ in range(2):
        user_client.post("/api/scans", files={"image": ("x.jpg", make_jpeg(), "image/jpeg")}, data={"lang": "en"})
    listing = user_client.get("/api/scans").json()
    assert len(listing["scans"]) == 2
    res = user_client.delete("/api/scans")
    assert res.json()["deleted"] == 2
    assert user_client.get("/api/scans").json()["scans"] == []


# ---------------------------------------------------------------- tracker

def test_application_lifecycle(user_client):
    res = user_client.post("/api/applications", json={
        "form_id": "passport-new", "office": "PSK Malad", "reference_no": "ARN-123",
        "target_date": "2099-01-01", "remind_days": 5, "notes": "keep receipt",
    })
    assert res.status_code == 200, res.text
    app_id = res.json()["id"]

    listing = user_client.get("/api/applications").json()
    assert listing["applications"][0]["form_name"] == "Passport (fresh application)"
    assert listing["applications"][0]["days_left"] > 0

    detail = user_client.get(f"/api/applications/{app_id}").json()
    assert detail["form"]["where_to_go"]["office"]
    assert detail["form"]["compulsory_documents"]

    patch = user_client.patch(f"/api/applications/{app_id}", json={"status": "submitted"})
    assert patch.status_code == 200
    events = user_client.get(f"/api/applications/{app_id}").json()["events"]
    assert [e["status"] for e in events] == ["started", "submitted"]

    bad = user_client.patch(f"/api/applications/{app_id}", json={"status": "teleported"})
    assert bad.status_code == 400

    assert user_client.delete(f"/api/applications/{app_id}").status_code == 200
    assert user_client.get(f"/api/applications/{app_id}").status_code == 404


def test_application_requires_name_or_known_form(user_client):
    res = user_client.post("/api/applications", json={"form_id": "", "form_name": ""})
    assert res.status_code == 400
    res = user_client.post("/api/applications", json={"form_id": "nonexistent", "form_name": ""})
    assert res.status_code == 404


def test_overdue_application_raises_warning(user_client):
    user_client.post("/api/applications", json={
        "form_name": "Custom old work", "target_date": "2000-01-01", "remind_days": 3,
    })
    alerts = user_client.get("/api/alerts").json()
    assert any(a["kind"] == "warning" and "target date passed" in a["title"] for a in alerts["alerts"])


def test_manual_alerts_crud(user_client):
    created = user_client.post("/api/alerts", json={
        "title": "Collect PAN card", "due_date": "2099-06-01", "body": "bring Aadhaar",
    })
    assert created.status_code == 200
    alert_id = created.json()["id"]
    items = user_client.get("/api/alerts").json()["alerts"]
    assert any(a.get("alert_id") == alert_id for a in items)
    assert user_client.patch(f"/api/alerts/{alert_id}", json={"read": True}).status_code == 200
    assert user_client.delete(f"/api/alerts/{alert_id}").status_code == 200


# ---------------------------------------------------------------- recommendations

def test_recommendations_for_farmer(user_client):
    res = user_client.get("/api/recommendations?role=farmer")
    assert res.status_code == 200
    data = res.json()
    ids = [s["id"] for s in data["for_you"]]
    assert "pm-kisan-scheme" in ids
    assert "cghs" not in ids
    pm = next(s for s in data["for_you"] if s["id"] == "pm-kisan-scheme")
    assert pm["benefits"] and pm["extra_costs"] and pm["where_to_go"] and pm["warnings"]
    assert all(pm["where_to_go"].values())


def test_recommendations_change_with_role(client):
    for email, role, expected in [
        ("doc@example.com", "doctor", "nmc-registration"),
        ("gov@example.com", "govt_employee", "cghs"),
        ("stud@example.com", "student", "nsp-scholarships"),
    ]:
        c = TestClientScope(client).__enter__()
        try:
            c.post("/api/auth/register", json={
                "email": email, "password": "strongpassword1", "name": "T",
                "role": role, "lang": "en", "area": "Delhi", "consent": True,
            })
            ids = [s["id"] for s in c.get("/api/recommendations").json()["for_you"]]
            assert expected in ids, (role, ids)
        finally:
            c.__exit__(None, None, None)


def test_scheme_details(client):
    res = client.get("/api/schemes/pm-kisan-scheme")
    assert res.status_code == 200
    assert "benefits" in res.json()
    assert client.get("/api/schemes/not-real").status_code == 404


# ---------------------------------------------------------------- centres + forms

def test_forms_directory(client):
    res = client.get("/api/forms")
    assert res.status_code == 200
    forms = res.json()["forms"]
    ids = [f["id"] for f in forms]
    assert "pan-new" in ids and "pm-kisan" in ids
    pan = next(f for f in forms if f["id"] == "pan-new")
    assert pan["where_to_go"]


def test_centres_search_by_service_and_area(client):
    res = client.get("/api/centres?service=passport&area=mumbai")
    assert res.status_code == 200
    centres = res.json()["centres"]
    assert centres and all("passport" in c["services"] for c in centres)
    assert any("Mumbai" in (c.get("district") or "") for c in centres)
    res = client.get("/api/centres?service=agriculture")
    assert any("agriculture" in c["services"] for c in res.json()["centres"])


# ---------------------------------------------------------------- PDF

def test_form_checklist_pdf_download(client):
    res = client.get("/api/pdf/form/pan-new?lang=hi")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment" in res.headers["content-disposition"]
    assert res.content[:5] == b"%PDF-"
    assert len(res.content) > 5000


def test_scheme_pdf_download(client):
    res = client.get("/api/pdf/scheme/pm-kisan-scheme?lang=mr")
    assert res.status_code == 200
    assert res.content[:5] == b"%PDF-"
    assert client.get("/api/pdf/scheme/nope").status_code == 404


def test_custom_checklist_pdf(client):
    res = client.post("/api/pdf/checklist", json={
        "title": "My list", "subtitle": "test", "lang": "en",
        "sections": [{"heading": "Docs", "items": ["Aadhaar", "Photo"]}],
    })
    assert res.status_code == 200
    assert res.content[:5] == b"%PDF-"


# ---------------------------------------------------------------- model endpoints without keys

def test_analyze_without_keys_returns_503(client):
    res = client.post("/api/analyze", files={"image": ("x.jpg", make_jpeg(), "image/jpeg")}, data={"lang": "en"})
    assert res.status_code == 503
    assert "gemini" in res.json()["error"].lower()


def test_chat_without_keys_returns_503(client):
    res = client.post("/api/chat", json={"message": "I need a passport"})
    assert res.status_code == 503


def test_analyze_rejects_bad_lang_and_bad_file(client):
    res = client.post("/api/analyze", files={"image": ("x.jpg", make_jpeg(), "image/jpeg")}, data={"lang": "xx"})
    assert res.status_code == 400
    res = client.post("/api/analyze", files={"image": ("x.txt", b"not an image", "text/plain")}, data={"lang": "en"})
    assert res.status_code == 400


# ---------------------------------------------------------------- tools

def test_chat_tools_execute_against_kb():
    from app import db, tools

    forms = db.get_forms()
    schemes = db.get_schemes()
    centres = db.get_centres()

    listed = tools.execute_tool("list_supported_forms", {}, forms, schemes, centres)
    assert any(f["id"] == "pan-new" for f in listed["forms"])

    sheet = tools.execute_tool("get_form_requirements", {"form_id": "pan-new"}, forms, schemes, centres)
    assert sheet["compulsory_documents"]

    scheme = tools.execute_tool("get_scheme_details", {"scheme_id": "cghs"}, forms, schemes, centres)
    assert "benefits" in scheme

    found = tools.execute_tool("find_centre", {"service": "tehsil", "area": "jaipur"}, forms, schemes, centres)
    assert found["centres"]
