"""P1 Task 3: phone numbers are encrypted at rest in alert_subscriptions
and webpush_subscriptions, and feedback audio clips are Fernet-encrypted
on disk.

Round-trip the /alerts/subscribe + /alerts/history flow through the
TestClient and assert that:
  1. the plaintext `phone` column does NOT contain raw E.164 (it is
     NULL on new writes);
  2. `phone_hash` is the expected peppered SHA-256;
  3. `phone_ciphertext` decrypts back to the original phone with
     FERNET_KEY;
  4. a follow-up GET /alerts/history (which JOINs by phone_hash) still
     returns the right rows.

A second test exercises the feedback-clip Fernet round-trip directly
against `_save_feedback_clip` — that is the on-disk PII vector for the
acoustic pipeline.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

import numpy as np
import pytest

# Ensure required settings exist before backend imports settle them.
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-please-rotate")
os.environ.setdefault("FAST2SMS_API_KEY", "")
os.environ.setdefault("APP_PEPPER", "test-pepper-thirty-two-chars-or-more-xxxxxx")
# Stable Fernet key for the test process (base64url, 32 bytes).
os.environ.setdefault("FERNET_KEY", "qOegLeb4SnGss64wQtnzEO2uBcRfjZSa0eO17YEFCFE=")


@pytest.fixture
def settings_singleton_clear():
    from backend.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(settings_singleton_clear, tmp_path, monkeypatch):
    """TestClient wired to an isolated SQLite file."""
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test_pii.db"))
    from backend.config import get_settings
    get_settings.cache_clear()
    import importlib, backend.main
    importlib.reload(backend.main)
    from backend.middleware.rate_limit import limiter
    try:
        limiter.reset()
    except Exception:
        pass
    from fastapi.testclient import TestClient
    with TestClient(backend.main.app) as c:
        yield c, str(tmp_path / "test_pii.db")


def test_subscribe_does_not_store_plaintext_phone(client, auth_headers, test_phone):
    c, db_path = client
    body = {
        "phone": test_phone,
        "district": "Pune",
        "state": "Maharashtra",
        "crops": ["Cotton"],
        "alert_types": ["frost"],
    }
    r = c.post("/api/alerts/subscribe", json=body, headers=auth_headers)
    assert r.status_code == 200, r.text
    # The response decrypts-on-read and echoes the original phone back.
    assert r.json()["phone"] == test_phone

    # Inspect the raw DB row directly — no ORM, no decryption.
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            "SELECT phone, phone_hash, phone_ciphertext FROM alert_subscriptions"
        ).fetchall()
    finally:
        con.close()
    assert len(rows) == 1
    phone_col, phone_hash, phone_ct = rows[0]

    # 1. Plaintext column must NOT contain raw E.164.
    assert phone_col is None, f"phone column should be NULL, got {phone_col!r}"

    # 2. phone_hash matches the peppered SHA-256.
    from backend.config import get_settings
    expected_hash = hashlib.sha256(
        (test_phone + get_settings().APP_PEPPER).encode("utf-8")
    ).hexdigest()
    assert phone_hash == expected_hash

    # 3. ciphertext decrypts back to the original phone with FERNET_KEY.
    from cryptography.fernet import Fernet
    decrypted = Fernet(get_settings().FERNET_KEY.encode()).decrypt(
        phone_ct.encode("utf-8")
    ).decode("utf-8")
    assert decrypted == test_phone

    # 4. Ciphertext must not embed the plaintext (sanity check on Fernet output).
    assert test_phone not in phone_ct


def test_alerts_history_lookup_uses_phone_hash(client, auth_headers, test_phone):
    """After subscribing the user fetches /alerts/history; the JOIN must
    resolve via phone_hash even though the plaintext `phone` column is
    NULL on the freshly-inserted row.
    """
    c, db_path = client
    body = {
        "phone": test_phone,
        "district": "Pune",
        "state": "Maharashtra",
        "crops": ["Cotton"],
        "alert_types": ["frost"],
    }
    sub_resp = c.post("/api/alerts/subscribe", json=body, headers=auth_headers)
    sub_id = sub_resp.json()["id"]

    # Manually seed an alert_history row for this subscription so /history
    # has something to return.
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """INSERT INTO alert_history
                   (subscription_id, alert_type, severity, message, sent_via)
               VALUES (?, 'frost', 'high', 'Test frost alert', 'sms')""",
            (sub_id,),
        )
        con.commit()
    finally:
        con.close()

    r = c.get("/api/alerts/history", headers=auth_headers)
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["alert_type"] == "frost"
    assert items[0]["message"] == "Test frost alert"


def test_push_subscribe_stores_phone_hash_and_ciphertext(client, auth_headers, test_phone):
    c, db_path = client
    body = {
        "phone": test_phone,
        "endpoint": "https://fcm.googleapis.com/test-endpoint-pii",
        "p256dh": "p256dh-key-stub",
        "auth": "auth-key-stub",
    }
    r = c.post("/api/alerts/push-subscribe", json=body, headers=auth_headers)
    assert r.status_code == 200, r.text

    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT phone, phone_hash, phone_ciphertext "
            "FROM webpush_subscriptions WHERE endpoint = ?",
            (body["endpoint"],),
        ).fetchone()
    finally:
        con.close()
    phone_col, phone_hash, phone_ct = row
    assert phone_col is None
    from backend.config import get_settings
    expected_hash = hashlib.sha256(
        (test_phone + get_settings().APP_PEPPER).encode("utf-8")
    ).hexdigest()
    assert phone_hash == expected_hash
    from cryptography.fernet import Fernet
    decrypted = Fernet(get_settings().FERNET_KEY.encode()).decrypt(
        phone_ct.encode("utf-8")
    ).decode("utf-8")
    assert decrypted == test_phone


def test_migrate_pii_backfills_legacy_rows(tmp_path, settings_singleton_clear, monkeypatch):
    """scripts/migrate_pii.py converts plaintext-`phone` rows into
    (phone_hash, phone_ciphertext) without altering id or other columns."""
    db_path = tmp_path / "legacy.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    from backend.config import get_settings
    get_settings.cache_clear()

    # First, hand-craft a legacy schema (no phone_hash / phone_ciphertext).
    con = sqlite3.connect(str(db_path))
    con.executescript(
        """
        CREATE TABLE alert_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            state TEXT NOT NULL,
            crops TEXT NOT NULL DEFAULT '[]',
            alert_types TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE webpush_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL DEFAULT '',
            auth TEXT NOT NULL DEFAULT ''
        );
        INSERT INTO alert_subscriptions (phone, state) VALUES ('+919876543210', 'Maharashtra');
        INSERT INTO alert_subscriptions (phone, state) VALUES ('+919000000001', 'Karnataka');
        INSERT INTO webpush_subscriptions (phone, endpoint) VALUES ('+919876543210', 'ep1');
        """
    )
    con.commit()
    con.close()

    # init_db adds the new columns + indexes idempotently.
    import asyncio
    from backend.services.db import init_db
    asyncio.run(init_db())

    # Now run the migration script's `main` directly.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "migrate_pii", str(Path(__file__).resolve().parent.parent / "scripts" / "migrate_pii.py")
    )
    migrate_pii = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migrate_pii)
    monkeypatch.setattr("sys.argv", ["migrate_pii.py", "--db", str(db_path)])
    rc = migrate_pii.main()
    assert rc == 0

    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute(
            "SELECT phone, phone_hash, phone_ciphertext FROM alert_subscriptions ORDER BY id"
        ).fetchall()
        webpush_rows = con.execute(
            "SELECT phone, phone_hash, phone_ciphertext FROM webpush_subscriptions"
        ).fetchall()
    finally:
        con.close()

    assert len(rows) == 2
    for phone_plain, phone_hash, phone_ct in rows:
        # Legacy plaintext is intentionally LEFT IN PLACE — nulling it
        # out is a follow-up destructive step (see migrate_pii.py docs).
        assert phone_plain in ("+919876543210", "+919000000001")
        assert phone_hash and len(phone_hash) == 64
        assert phone_ct
        from backend.config import get_settings
        from cryptography.fernet import Fernet
        decrypted = Fernet(get_settings().FERNET_KEY.encode()).decrypt(
            phone_ct.encode("utf-8")
        ).decode("utf-8")
        assert decrypted == phone_plain
    assert len(webpush_rows) == 1
    assert webpush_rows[0][1] and webpush_rows[0][2]


def test_feedback_clip_is_encrypted_on_disk(tmp_path, settings_singleton_clear, monkeypatch):
    """`_save_feedback_clip` must Fernet-encrypt bytes before writing.

    Asserts both that the on-disk payload is NOT a valid RIFF/WAV header
    (Fernet output starts with the 0x80 version byte) and that the
    payload round-trips through Fernet decryption.
    """
    from backend.routers import acoustic
    # Redirect the feedback-clip dir into the tmp_path so we don't pollute
    # data/feedback_clips/ when the test runs.
    monkeypatch.setattr(acoustic, "FEEDBACK_CLIPS_DIR", tmp_path)
    # Synthesise 1 second of 440 Hz mono float PCM at 16 kHz.
    rate = 16000
    t = np.linspace(0, 1.0, rate, endpoint=False)
    pcm = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    clip_id = acoustic._save_feedback_clip(pcm, rate)
    out = tmp_path / f"{clip_id}.wav"
    assert out.exists()

    payload = out.read_bytes()
    # WAV files start with the ASCII "RIFF" magic. Fernet tokens are
    # base64url-encoded — they cannot start with "RIFF". This is the
    # core "unplayable without the key" guarantee.
    assert not payload.startswith(b"RIFF")

    from backend.config import get_settings
    from cryptography.fernet import Fernet
    decrypted = Fernet(get_settings().FERNET_KEY.encode()).decrypt(payload)
    # Once decrypted, the plaintext is a normal RIFF-headed WAV file.
    assert decrypted.startswith(b"RIFF")
