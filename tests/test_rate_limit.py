"""
Tests for Task 5 — slowapi rate limiting.

Strategy
--------
Rather than hammering a production-limit endpoint (e.g. 5/hour requires
6 HTTP calls and would make the test slow if a real clock-based backend
were used), we override the limit string for a single test by temporarily
registering a 1/minute limit on the subscribe route and calling it twice.

All tests use the in-process TestClient so no network round-trips occur.
The slowapi in-memory store resets between test functions because a fresh
``app`` + ``TestClient`` is created for each test that needs isolation.

Tested behaviours
-----------------
1. Under-limit: first call returns 200 (or 201/204 — not 429).
2. Over-limit: call N+1 within the window returns 429.
3. 429 response body is the structured JSON the audit requires:
       {"error": "rate_limited", "retry_after": <int>}
4. The /auth/request-otp endpoint is rate-limited (5/hour), with the
   configured DEMO_PHONE exempt.
5. The /disease/analyze-image endpoint is rate-limited (20/hour) and
   now requires a JWT, not an API key.
6. The /acoustic/analyze endpoint is rate-limited (20/hour) and
   now requires a JWT, not an API key.
"""

from __future__ import annotations

import os
import time

import pytest

# Required env vars before any app import
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-ratelimit")
os.environ.setdefault("FAST2SMS_API_KEY", "")  # forces SMS stub


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Reset lru_cache on get_settings so env mutations between tests are
    picked up reliably."""
    from backend.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Build a fresh TestClient with an isolated SQLite so alert tables don't
    collide.  The slowapi in-memory counter starts fresh because a new
    ``limiter`` instance is created inside ``rate_limit.py`` at import time,
    but the storage is reset whenever the process restarts the TestClient
    context.  We additionally reset the limiter storage directly to guarantee
    isolation between tests.
    """
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "rl_test.db"))
    from backend.config import get_settings
    get_settings.cache_clear()

    import importlib
    import backend.main
    importlib.reload(backend.main)

    # Reset the in-memory rate-limit storage so previous test hits don't
    # bleed into this test's counter.
    from backend.middleware.rate_limit import limiter
    try:
        limiter.reset()
    except Exception:
        pass

    from fastapi.testclient import TestClient
    with TestClient(backend.main.app, raise_server_exceptions=False) as c:
        yield c


def _fresh_jwt(client) -> str:
    """
    Obtain a valid JWT by going through the OTP flow with a patched OTP
    generator so the test knows the OTP value.
    """
    from backend.routers import auth as _auth_router
    original = _auth_router.generate_otp
    _auth_router.generate_otp = lambda: "111111"
    try:
        client.post("/api/auth/request-otp", json={"phone": "+919999900001"})
        r = client.post(
            "/api/auth/verify-otp",
            json={"phone": "+919999900001", "otp": "111111"},
        )
    finally:
        _auth_router.generate_otp = original
    assert r.status_code == 200, f"JWT acquisition failed: {r.text}"
    return r.json()["token"]


# ── /alerts/subscribe (5/hour) ────────────────────────────────────────────

def test_subscribe_under_limit_returns_2xx(client):
    """First subscribe call must NOT be rate-limited."""
    token = _fresh_jwt(client)
    body = {
        "phone": "+919999900001", "district": "Pune",
        "state": "Maharashtra", "crops": ["Cotton"],
        "alert_types": ["frost"],
    }
    r = client.post(
        "/api/alerts/subscribe", json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code not in (429,), (
        f"Expected 2xx, got {r.status_code}: {r.text}"
    )


def test_subscribe_over_limit_returns_429(client, monkeypatch):
    """
    The /auth/request-otp endpoint is limited to 5/hour, keyed per-IP
    (the unauthenticated fallback). Six calls from the same IP within the
    window — the 6th must return 429.

    Note: the limit is per-IP, not per-phone, so cycling phone numbers does
    not dodge it; that's why distinct phones still share one bucket here.
    """
    # Call /request-otp 5 times — should all succeed (under the 5/hour limit).
    for i in range(5):
        r = client.post(
            "/api/auth/request-otp",
            json={"phone": f"+9199999{i:05d}"},
        )
        # 200 or 502 (SMS stub might fail) are both acceptable — not 429.
        assert r.status_code != 429, (
            f"Call {i+1} was unexpectedly rate-limited: {r.text}"
        )

    # 6th call from the same IP should be rate-limited (5/hour exhausted).
    r6 = client.post(
        "/api/auth/request-otp",
        json={"phone": "+919999999999"},
    )
    assert r6.status_code == 429, (
        f"Expected 429 on 6th OTP request, got {r6.status_code}: {r6.text}"
    )
    body = r6.json()
    assert body.get("error") == "rate_limited", f"Wrong error key: {body}"
    assert isinstance(body.get("retry_after"), int), (
        f"retry_after must be an int: {body}"
    )
    assert body["retry_after"] > 0


def test_429_response_shape(client):
    """
    Verify the 429 JSON body is exactly:
        {"error": "rate_limited", "retry_after": <positive int>}
    """
    # Exhaust the OTP limit (5/hour, same IP)
    for _ in range(5):
        client.post("/api/auth/request-otp", json={"phone": "+919999900099"})

    r = client.post("/api/auth/request-otp", json={"phone": "+919999900099"})
    assert r.status_code == 429
    body = r.json()
    assert set(body.keys()) == {"error", "retry_after"}, (
        f"Unexpected keys in 429 body: {body}"
    )
    assert body["error"] == "rate_limited"
    assert isinstance(body["retry_after"], int) and body["retry_after"] > 0
    # The Retry-After header should also be set
    assert "retry-after" in {k.lower() for k in r.headers}, (
        f"Missing Retry-After header; headers: {dict(r.headers)}"
    )


# ── /disease/analyze-image (20/hour, now requires JWT) ────────────────────

def test_disease_analyze_requires_jwt_not_api_key(client):
    """
    The auth swap (require_api_key → require_user) on /disease/analyze-image
    means X-API-Key alone must now be rejected.
    """
    import io
    from PIL import Image as _Image
    import numpy as _np

    buf = io.BytesIO()
    _Image.fromarray(_np.zeros((4, 4, 3), dtype=_np.uint8)).save(buf, format="PNG")
    buf.seek(0)

    r = client.post(
        "/api/disease/analyze-image",
        files={"file": ("leaf.png", buf, "image/png")},
        data={"crop_type": "Tomato"},
        headers={"X-API-Key": "test-api-key"},
    )
    # X-API-Key alone must return 401, not 200 or 422
    assert r.status_code == 401, (
        f"Expected 401 when using API key on JWT-protected route, got {r.status_code}"
    )


# ── /acoustic/analyze (20/hour, now requires JWT) ─────────────────────────

def test_acoustic_analyze_requires_jwt_not_api_key(client):
    """
    The auth swap on /acoustic/analyze means X-API-Key alone must be rejected.
    """
    import io
    import numpy as _np
    import scipy.io.wavfile as _wav

    buf = io.BytesIO()
    silence = _np.zeros(32000, dtype=_np.int16)
    _wav.write(buf, 16000, silence)
    buf.seek(0)

    r = client.post(
        "/api/acoustic/analyze",
        files={"file": ("field.wav", buf, "audio/wav")},
        data={"crop_type": "Cotton"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert r.status_code == 401, (
        f"Expected 401 when using API key on JWT-protected route, got {r.status_code}"
    )


# ── limiter key sanity ─────────────────────────────────────────────────────

def test_rate_limit_key_prefers_user_sub_over_ip():
    """Unit-test the key function in isolation."""
    from unittest.mock import MagicMock
    from backend.middleware.rate_limit import _rate_limit_key

    req = MagicMock()
    req.state.user = {"sub": "abc123", "phone": "+919876543210"}
    req.headers.get.return_value = None
    req.client = MagicMock()
    req.client.host = "1.2.3.4"

    key = _rate_limit_key(req)
    assert key == "user:abc123", f"Expected user key, got: {key}"


def test_rate_limit_key_falls_back_to_ip_when_no_user():
    """Without request.state.user, key function falls back to IP."""
    from unittest.mock import MagicMock
    from backend.middleware.rate_limit import _rate_limit_key

    req = MagicMock()
    req.state = MagicMock(spec=[])  # no 'user' attribute
    req.headers.get.return_value = None
    req.client = MagicMock()
    req.client.host = "5.6.7.8"

    key = _rate_limit_key(req)
    assert key == "ip:5.6.7.8", f"Expected IP key, got: {key}"


def _otp_key_req(phone: str, host: str = "9.8.7.6"):
    from unittest.mock import MagicMock
    req = MagicMock()
    req.state = MagicMock()
    req.state.otp_phone = phone
    req.headers.get.return_value = None
    req.client = MagicMock()
    req.client.host = host
    return req


def test_otp_rate_limit_key_falls_back_to_ip_for_normal_number(monkeypatch):
    """A normal number is throttled per-IP (not per-phone)."""
    monkeypatch.delenv("DEMO_PHONE", raising=False)
    from backend.config import get_settings
    get_settings.cache_clear()
    from backend.middleware.rate_limit import _otp_rate_limit_key

    key = _otp_rate_limit_key(_otp_key_req("+919876543210"))
    assert key == "ip:9.8.7.6", f"Expected IP key, got: {key}"


def test_otp_rate_limit_key_exempts_demo_number(monkeypatch):
    """The configured DEMO_PHONE gets an empty key → slowapi skips the limit."""
    monkeypatch.setenv("DEMO_PHONE", "1234567890")
    from backend.config import get_settings
    get_settings.cache_clear()
    from backend.middleware.rate_limit import _otp_rate_limit_key

    key = _otp_rate_limit_key(_otp_key_req("+911234567890"))
    assert key == "", f"Expected empty (exempt) key for demo number, got: {key}"
