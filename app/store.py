"""SQLite persistence: users, encrypted scan vault, paperwork tracker, alerts.

One connection guarded by a lock (a single-process demo server). WAL mode for
read performance. No document text, no analysis content and no passwords in
plaintext columns: sensitive JSON lives in *_enc BLOB columns, encrypted per
user (see security.py).
"""
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager

from . import config

_lock = threading.RLock()
_conn = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'citizen',
    lang TEXT NOT NULL DEFAULT 'en',
    area TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    consented_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    label_enc BLOB,
    blob_enc BLOB NOT NULL,
    analysis_enc BLOB,
    lang TEXT NOT NULL DEFAULT 'en',
    mime TEXT NOT NULL DEFAULT 'image/jpeg',
    size INTEGER NOT NULL DEFAULT 0,
    sha256 TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    expires_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    form_id TEXT NOT NULL DEFAULT '',
    form_name TEXT NOT NULL,
    office TEXT NOT NULL DEFAULT '',
    reference_no TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'started',
    target_date TEXT,
    notes TEXT NOT NULL DEFAULT '',
    remind_days INTEGER NOT NULL DEFAULT 3,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS app_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    at TEXT NOT NULL,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    due_date TEXT,
    kind TEXT NOT NULL DEFAULT 'reminder',
    read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS security_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL,
    ip TEXT NOT NULL DEFAULT '',
    at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scans_user ON scans(user_id);
CREATE INDEX IF NOT EXISTS idx_apps_user ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_events_app ON app_events(application_id);
CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id);
"""

STATUSES = (
    "started",
    "documents_gathered",
    "submitted",
    "under_review",
    "action_needed",
    "approved",
    "rejected",
    "completed",
)


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _connect():
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


@contextmanager
def _tx():
    with _lock:
        conn = _connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def init_db():
    with _tx() as conn:
        conn.executescript(SCHEMA)


def reset_for_tests():
    """Close and forget the connection so a new DB path can be used."""
    global _conn
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:  # noqa: BLE001
                pass
            _conn = None


def _row_to_dict(row):
    return dict(row) if row is not None else None


# ---------------------------------------------------------------- users

def create_user(email, name, password_hash, role="citizen", lang="en", area="", phone="", consented=True):
    ts = now_iso()
    with _tx() as conn:
        cur = conn.execute(
            "INSERT INTO users (email, name, password_hash, role, lang, area, phone, consented_at, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (email.lower().strip(), name.strip(), password_hash, role, lang, area.strip(), phone.strip(),
             ts if consented else None, ts, ts),
        )
        return cur.lastrowid


def get_user_by_email(email):
    with _lock:
        row = _connect().execute(
            "SELECT * FROM users WHERE lower(email) = ?", (email.lower().strip(),)
        ).fetchone()
    return _row_to_dict(row)


def get_user(user_id):
    with _lock:
        row = _connect().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_dict(row)


def update_user(user_id, **fields):
    allowed = {"name", "role", "lang", "area", "phone", "password_hash"}
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return
    sets["updated_at"] = now_iso()
    cols = ", ".join(f"{k} = ?" for k in sets)
    with _tx() as conn:
        conn.execute(f"UPDATE users SET {cols} WHERE id = ?", (*sets.values(), user_id))


def delete_user(user_id):
    """Hard delete: the user row and every derived row cascade away."""
    with _tx() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def count_users():
    with _lock:
        return _connect().execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]


def log_security(email, action, ip=""):
    with _tx() as conn:
        conn.execute(
            "INSERT INTO security_log (email, action, ip, at) VALUES (?,?,?,?)",
            (email.lower().strip(), action, ip, now_iso()),
        )


# ---------------------------------------------------------------- scans

def create_scan(user_id, blob_enc, label_enc=None, analysis_enc=None, lang="en", mime="image/jpeg", sha256=""):
    """Store an encrypted scan. The blob only ever exists encrypted, in SQLite."""
    ts = now_iso()
    expires = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ",
        time.gmtime(time.time() + config.SCAN_RETENTION_DAYS * 86400),
    )
    with _tx() as conn:
        cur = conn.execute(
            "INSERT INTO scans (user_id, label_enc, blob_enc, analysis_enc, lang, mime, size, sha256, created_at, expires_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (user_id, label_enc, blob_enc, analysis_enc, lang, mime, len(blob_enc), sha256, ts, expires),
        )
        return cur.lastrowid


def list_scans(user_id):
    with _lock:
        rows = _connect().execute(
            "SELECT id, label_enc, analysis_enc, lang, mime, size, created_at, expires_at"
            " FROM scans WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def count_scans(user_id):
    with _lock:
        return _connect().execute(
            "SELECT COUNT(*) AS n FROM scans WHERE user_id = ?", (user_id,)
        ).fetchone()["n"]


def get_scan(user_id, scan_id):
    with _lock:
        row = _connect().execute(
            "SELECT * FROM scans WHERE id = ? AND user_id = ?", (scan_id, user_id)
        ).fetchone()
    return _row_to_dict(row)


def update_scan_label(user_id, scan_id, label_enc):
    with _tx() as conn:
        conn.execute(
            "UPDATE scans SET label_enc = ? WHERE id = ? AND user_id = ?",
            (label_enc, scan_id, user_id),
        )


def update_scan_analysis(user_id, scan_id, analysis_enc, lang=None):
    with _tx() as conn:
        if lang:
            conn.execute(
                "UPDATE scans SET analysis_enc = ?, lang = ? WHERE id = ? AND user_id = ?",
                (analysis_enc, lang, scan_id, user_id),
            )
        else:
            conn.execute(
                "UPDATE scans SET analysis_enc = ? WHERE id = ? AND user_id = ?",
                (analysis_enc, scan_id, user_id),
            )


def delete_scan(user_id, scan_id):
    with _tx() as conn:
        cur = conn.execute("DELETE FROM scans WHERE id = ? AND user_id = ?", (scan_id, user_id))
        return cur.rowcount > 0


def delete_all_scans(user_id):
    with _tx() as conn:
        cur = conn.execute("DELETE FROM scans WHERE user_id = ?", (user_id,))
        return cur.rowcount


def cleanup_expired_scans():
    """Delete scans past their retention date. Returns the number removed."""
    with _tx() as conn:
        cur = conn.execute(
            "DELETE FROM scans WHERE expires_at IS NOT NULL AND expires_at < ?", (now_iso(),)
        )
        return cur.rowcount


# ---------------------------------------------------------------- applications

def create_application(user_id, form_id, form_name, office="", reference_no="", target_date=None,
                       notes="", remind_days=3):
    ts = now_iso()
    with _tx() as conn:
        cur = conn.execute(
            "INSERT INTO applications (user_id, form_id, form_name, office, reference_no, status, target_date, notes, remind_days, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (user_id, form_id, form_name, office, reference_no, "started", target_date, notes, remind_days, ts, ts),
        )
        app_id = cur.lastrowid
        conn.execute(
            "INSERT INTO app_events (application_id, status, note, at) VALUES (?,?,?,?)",
            (app_id, "started", "Application tracked in Samajh.", ts),
        )
    return app_id


def list_applications(user_id):
    with _lock:
        rows = _connect().execute(
            "SELECT * FROM applications WHERE user_id = ? ORDER BY id DESC", (user_id,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_application(user_id, app_id):
    with _lock:
        row = _connect().execute(
            "SELECT * FROM applications WHERE id = ? AND user_id = ?", (app_id, user_id)
        ).fetchone()
    return _row_to_dict(row)


def update_application(user_id, app_id, **fields):
    allowed = {"office", "reference_no", "status", "target_date", "notes", "remind_days", "form_name"}
    sets = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not sets:
        return False
    sets["updated_at"] = now_iso()
    cols = ", ".join(f"{k} = ?" for k in sets)
    with _tx() as conn:
        cur = conn.execute(
            f"UPDATE applications SET {cols} WHERE id = ? AND user_id = ?",
            (*sets.values(), app_id, user_id),
        )
        return cur.rowcount > 0


def add_app_event(user_id, app_id, status, note=""):
    ts = now_iso()
    with _tx() as conn:
        owns = conn.execute(
            "SELECT id FROM applications WHERE id = ? AND user_id = ?", (app_id, user_id)
        ).fetchone()
        if not owns:
            return None
        conn.execute(
            "INSERT INTO app_events (application_id, status, note, at) VALUES (?,?,?,?)",
            (app_id, status, note, ts),
        )
        conn.execute(
            "UPDATE applications SET status = ?, updated_at = ? WHERE id = ?",
            (status, ts, app_id),
        )
        return ts


def list_events(app_id):
    with _lock:
        rows = _connect().execute(
            "SELECT * FROM app_events WHERE application_id = ? ORDER BY id ASC", (app_id,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def delete_application(user_id, app_id):
    with _tx() as conn:
        cur = conn.execute(
            "DELETE FROM applications WHERE id = ? AND user_id = ?", (app_id, user_id)
        )
        return cur.rowcount > 0


# ---------------------------------------------------------------- alerts

def create_alert(user_id, title, body="", due_date=None, kind="reminder"):
    with _tx() as conn:
        cur = conn.execute(
            "INSERT INTO alerts (user_id, title, body, due_date, kind, read, created_at) VALUES (?,?,?,?,?,0,?)",
            (user_id, title, body, due_date, kind, now_iso()),
        )
        return cur.lastrowid


def list_alerts(user_id):
    with _lock:
        rows = _connect().execute(
            "SELECT * FROM alerts WHERE user_id = ? ORDER BY read ASC, id DESC", (user_id,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def set_alert_read(user_id, alert_id, read=True):
    with _tx() as conn:
        cur = conn.execute(
            "UPDATE alerts SET read = ? WHERE id = ? AND user_id = ?",
            (1 if read else 0, alert_id, user_id),
        )
        return cur.rowcount > 0


def delete_alert(user_id, alert_id):
    with _tx() as conn:
        cur = conn.execute(
            "DELETE FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id)
        )
        return cur.rowcount > 0


# ---------------------------------------------------------------- export

def export_user_data(user_id):
    """Everything we hold, for the data-export (right of access) feature.

    Scan blobs are not exported (they are the user's own files and can be
    downloaded individually); analysis text is decrypted by the caller.
    """
    with _lock:
        conn = _connect()
        user = _row_to_dict(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
        apps = [_row_to_dict(r) for r in conn.execute(
            "SELECT * FROM applications WHERE user_id = ?", (user_id,)).fetchall()]
        scans = [_row_to_dict(r) for r in conn.execute(
            "SELECT id, lang, mime, size, created_at, expires_at FROM scans WHERE user_id = ?",
            (user_id,)).fetchall()]
        alerts = [_row_to_dict(r) for r in conn.execute(
            "SELECT * FROM alerts WHERE user_id = ?", (user_id,)).fetchall()]
    if user:
        user.pop("password_hash", None)
    for a in apps:
        a["events"] = list_events(a["id"])
    return {"user": user, "applications": apps, "scans": scans, "alerts": alerts}
