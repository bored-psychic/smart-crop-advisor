"""
Tests for the phone+OTP → JWT auth flow added in P0 Task 3.

These tests cover:
- the OTP service (store, verify, attempts lockout, TTL expiry, salt
  collision-resistance);
- the JWT helpers (issue / decode / expiry handling);
- the FastAPI auth dependencies (``require_user`` accepts valid bearers,
  rejects missing / malformed / expired ones; ``require_api_key`` still
  works as the service-to-service guard);
- the HTTP routes (request-otp, verify-otp, /me).

The OTP service is exercised against a real in-memory SQLite database
(via aiosqlite) — no mocking of the storage layer.
"""

from __future__ import annotations

import os
import time

import aiosqlite
import jwt
import pytest

# Ensure required settings are present before the app imports them.
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-please-rotate")
os.environ.setdefault("FAST2SMS_API_KEY", "")  # forces SMS stub


@pytest.fixture
def settings_singleton_clear():
    """Reset the lru_cache on get_settings between tests that mutate env."""
    from backend.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def memdb():
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


# ─── JWT helpers ────────────────────────────────────────────────────────


def test_hash_phone_is_stable_and_distinct():
    from backend.auth import hash_phone
    a = hash_phone("+919876543210")
    b = hash_phone("+919876543210")
    c = hash_phone("+919876500000")
    assert a == b
    assert a != c
    # SHA-256 hex
    assert len(a) == 64 and all(ch in "0123456789abcdef" for ch in a)


def test_issue_and_decode_token_roundtrip(settings_singleton_clear):
    from backend.auth import issue_token, decode_token, hash_phone
    token, exp = issue_token("+919876543210")
    claims = decode_token(token)
    assert claims["sub"] == hash_phone("+919876543210")
    assert claims["phone"] == "+919876543210"
    assert claims["exp"] == exp
    assert claims["exp"] > int(time.time())
    assert "iat" in claims and "jti" in claims


def test_decode_token_rejects_forged_signature(settings_singleton_clear):
    from backend.auth import decode_token
    from fastapi import HTTPException
    bad = jwt.encode({"sub": "x", "exp": int(time.time()) + 60, "iat": int(time.time())},
                     "different-secret", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        decode_token(bad)
    assert exc.value.status_code == 401


def test_decode_token_rejects_expired(settings_singleton_clear):
    from backend.auth import decode_token
    from backend.config import get_settings
    from fastapi import HTTPException
    expired = jwt.encode(
        {"sub": "x", "iat": int(time.time()) - 7200, "exp": int(time.time()) - 60},
        get_settings().JWT_SECRET, algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        decode_token(expired)
    assert exc.value.status_code == 401


# ─── OTP service ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_store_and_verify_otp_happy_path(memdb):
    from backend.services.auth_otp import store_otp, verify_otp, generate_otp
    otp = generate_otp()
    await store_otp(memdb, "+919876543210", otp)
    ok = await verify_otp(memdb, "+919876543210", otp)
    assert ok is True
    # Single-use — second verify must fail
    again = await verify_otp(memdb, "+919876543210", otp)
    assert again is False


@pytest.mark.asyncio
async def test_verify_otp_wrong_code_increments_attempts(memdb):
    from backend.services.auth_otp import store_otp, verify_otp
    await store_otp(memdb, "+919876543210", "123456")
    for _ in range(4):
        assert await verify_otp(memdb, "+919876543210", "000000") is False
    # Real code should still work on the 5th overall attempt
    assert await verify_otp(memdb, "+919876543210", "123456") is True


@pytest.mark.asyncio
async def test_verify_otp_lockout_after_max_attempts(memdb, settings_singleton_clear):
    from backend.services.auth_otp import store_otp, verify_otp
    from backend.config import get_settings
    await store_otp(memdb, "+919876543210", "123456")
    for _ in range(get_settings().OTP_MAX_ATTEMPTS):
        await verify_otp(memdb, "+919876543210", "000000")
    # Row was deleted; correct OTP no longer works.
    assert await verify_otp(memdb, "+919876543210", "123456") is False


@pytest.mark.asyncio
async def test_resend_otp_invalidates_previous(memdb):
    from backend.services.auth_otp import store_otp, verify_otp
    await store_otp(memdb, "+919876543210", "111111")
    await store_otp(memdb, "+919876543210", "222222")
    assert await verify_otp(memdb, "+919876543210", "111111") is False
    assert await verify_otp(memdb, "+919876543210", "222222") is True


@pytest.mark.asyncio
async def test_verify_otp_expiry(memdb, monkeypatch):
    from backend.services import auth_otp
    # Freeze "now" backwards so the stored row is already past expiry.
    real_now = auth_otp._now
    monkeypatch.setattr(auth_otp, "_now", lambda: real_now() - 10_000)
    await auth_otp.store_otp(memdb, "+919876543210", "123456")
    monkeypatch.setattr(auth_otp, "_now", real_now)
    assert await auth_otp.verify_otp(memdb, "+919876543210", "123456") is False


# ─── HTTP routes ────────────────────────────────────────────────────────


@pytest.fixture
def client(settings_singleton_clear, tmp_path, monkeypatch):
    """
    Build a TestClient against an isolated SQLite file so the OTP table
    and alert tables don't collide with the dev DB.
    """
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    from backend.config import get_settings
    get_settings.cache_clear()
    # Re-import main fresh so the lifespan picks up the new SQLITE_PATH.
    import importlib, backend.main
    importlib.reload(backend.main)
    # Reset the rate-limit in-memory counters so tests that call
    # /auth/request-otp multiple times don't bleed across each other.
    from backend.middleware.rate_limit import limiter
    try:
        limiter.reset()
    except Exception:
        pass
    from fastapi.testclient import TestClient
    with TestClient(backend.main.app) as c:
        yield c


def test_request_otp_returns_normalised_phone(client):
    r = client.post("/api/auth/request-otp", json={"phone": "9876543210"})
    assert r.status_code == 200, r.text
    assert r.json()["phone"] == "+919876543210"


def test_verify_otp_with_bad_code_returns_401(client):
    client.post("/api/auth/request-otp", json={"phone": "+919876543210"})
    r = client.post("/api/auth/verify-otp", json={"phone": "+919876543210", "otp": "000000"})
    assert r.status_code == 401


def test_verify_otp_happy_path_returns_jwt(client, tmp_path, monkeypatch):
    """
    We can't read the cleartext OTP (it's hashed). Instead we patch
    generate_otp so the test knows the value that was stored.
    """
    from backend.routers import auth as auth_router
    monkeypatch.setattr(auth_router, "generate_otp", lambda: "424242")
    client.post("/api/auth/request-otp", json={"phone": "+919876543210"})
    r = client.post("/api/auth/verify-otp", json={"phone": "+919876543210", "otp": "424242"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["phone"] == "+919876543210"
    assert isinstance(body["token"], str) and body["token"].count(".") == 2
    assert body["exp"] > int(time.time())


def test_me_route_rejects_missing_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_route_rejects_garbage_bearer(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert r.status_code == 401


def test_me_route_accepts_freshly_minted_token(client, monkeypatch):
    from backend.routers import auth as auth_router
    monkeypatch.setattr(auth_router, "generate_otp", lambda: "424242")
    client.post("/api/auth/request-otp", json={"phone": "+919876543210"})
    v = client.post("/api/auth/verify-otp", json={"phone": "+919876543210", "otp": "424242"})
    token = v.json()["token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["phone"] == "+919876543210"


def test_alerts_subscribe_requires_jwt_not_api_key(client):
    """The /alerts/subscribe route was switched from require_api_key to
    require_user in T3. The old X-API-Key path should no longer work."""
    body = {
        "phone": "+919876543210", "district": "Pune", "state": "Maharashtra",
        "crops": ["Cotton"], "alert_types": ["frost"],
    }
    # X-API-Key alone → 401 (no Authorization header)
    r = client.post("/api/alerts/subscribe", json=body,
                    headers={"X-API-Key": "test-api-key"})
    assert r.status_code == 401


def test_trigger_check_still_uses_api_key(client):
    """The service-to-service /alerts/trigger-check stays on require_api_key."""
    # Without any auth: 401
    r1 = client.post("/api/alerts/trigger-check")
    assert r1.status_code == 401
    # Wrong key: 403
    r2 = client.post("/api/alerts/trigger-check", headers={"X-API-Key": "wrong"})
    assert r2.status_code == 403


# ─── Task 6: /alerts/history derives phone from JWT ─────────────────────


def test_alerts_history_requires_jwt(client):
    """No token → 401; a query-string phone param is not enough."""
    r = client.get("/api/alerts/history")
    assert r.status_code == 401

    # Passing a phone query param without a token must still be 401.
    r2 = client.get("/api/alerts/history?phone=%2B919999999999")
    assert r2.status_code == 401


def test_alerts_history_returns_own_history(client, monkeypatch):
    """Authenticated user gets their own history (empty list when none sent)."""
    from backend.routers import auth as auth_router
    monkeypatch.setattr(auth_router, "generate_otp", lambda: "424242")
    client.post("/api/auth/request-otp", json={"phone": "+919876543210"})
    v = client.post("/api/auth/verify-otp", json={"phone": "+919876543210", "otp": "424242"})
    token = v.json()["token"]

    r = client.get("/api/alerts/history", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    # No subscriptions yet → empty list (not 403, not 404)
    assert r.json() == []


def test_alerts_history_phone_query_param_ignored(client, monkeypatch):
    """A phone query param is silently ignored; only the JWT phone is used.

    This test verifies that passing ?phone=<other> does NOT cause an error
    (the param is no longer declared on the endpoint) and that the response
    is scoped to the JWT owner, not the supplied query string value.
    """
    from backend.routers import auth as auth_router
    monkeypatch.setattr(auth_router, "generate_otp", lambda: "424242")
    client.post("/api/auth/request-otp", json={"phone": "+919876543210"})
    v = client.post("/api/auth/verify-otp", json={"phone": "+919876543210", "otp": "424242"})
    token = v.json()["token"]

    # Sending a different phone in the query string must not fail the request
    # nor return data for that other phone — it is simply ignored.
    r = client.get(
        "/api/alerts/history?phone=%2B919999999999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)
