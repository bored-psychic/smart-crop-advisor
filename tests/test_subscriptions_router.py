"""Tests for the alert subscriptions router (/api/alerts/).

Covers the subscribe / list (history) / unsubscribe lifecycle plus
authentication and phone validation checks.

Uses a temporary SQLite database (per-session) with the latest schema so
tests don't depend on the state of the development `kisanos.db`.
"""
from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """TestClient wrapping the app with a fresh temporary SQLite database."""
    # Use a temp db with the new schema (phone nullable) so the PII-aware
    # INSERT (phone=NULL, phone_hash=..., phone_ciphertext=...) works.
    tmp_db = tmp_path_factory.mktemp("db") / "test_subscriptions.db"

    # Patch settings before importing app so init_db uses the temp path.
    import backend.config as cfg_module
    original_cache = cfg_module.get_settings.cache_info  # save cache state check

    # Clear the lru_cache so get_settings picks up the new env var.
    cfg_module.get_settings.cache_clear()
    os.environ["SQLITE_PATH"] = str(tmp_db)

    from backend.main import app
    import asyncio
    from backend.services.db import init_db
    asyncio.run(init_db())

    with TestClient(app) as c:
        yield c

    # Restore
    cfg_module.get_settings.cache_clear()
    if "SQLITE_PATH" in os.environ:
        del os.environ["SQLITE_PATH"]


_VALID_SUBSCRIBE = {
    "phone": "+919999999999",
    "state": "Karnataka",
    "district": "Bangalore",
    "crops": ["Rice", "Wheat"],
    "alert_types": ["frost", "heavy_rain", "pest_risk"],
}


# ---------------------------------------------------------------------------
# Subscribe with valid phone → 200
# ---------------------------------------------------------------------------

def test_subscribe_happy_path(client, auth_headers):
    """POST /api/alerts/subscribe with valid payload returns 200."""
    resp = client.post(
        "/api/alerts/subscribe",
        json=_VALID_SUBSCRIBE,
        headers=auth_headers,
    )
    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert "id" in data
    assert data["phone"] == _VALID_SUBSCRIBE["phone"]
    assert data["state"] == _VALID_SUBSCRIBE["state"]
    assert set(data["crops"]) == set(_VALID_SUBSCRIBE["crops"])


# ---------------------------------------------------------------------------
# List subscriptions / alert history → 200
# ---------------------------------------------------------------------------

def test_alert_history_returns_200(client, auth_headers):
    """GET /api/alerts/history returns 200 with a list (may be empty)."""
    resp = client.get(
        "/api/alerts/history",
        headers=auth_headers,
    )
    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert isinstance(data, list), f"Expected list, got {type(data)}"


# ---------------------------------------------------------------------------
# Unsubscribe → 200
# ---------------------------------------------------------------------------

def test_unsubscribe_happy_path(client, auth_headers):
    """DELETE /api/alerts/unsubscribe/{id} returns 200 for an existing id."""
    # First create a subscription so we have a valid ID.
    sub_resp = client.post(
        "/api/alerts/subscribe",
        json=_VALID_SUBSCRIBE,
        headers=auth_headers,
    )
    assert sub_resp.status_code == 200
    sub_id = sub_resp.json()["id"]

    resp = client.delete(
        f"/api/alerts/unsubscribe/{sub_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200, (
        f"Expected 200 on unsubscribe, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert "message" in data


# ---------------------------------------------------------------------------
# No JWT → 401 on all three endpoints
# ---------------------------------------------------------------------------

def test_subscribe_requires_auth(client):
    """POST /api/alerts/subscribe without JWT returns 401."""
    resp = client.post("/api/alerts/subscribe", json=_VALID_SUBSCRIBE)
    assert resp.status_code in (401, 403)


def test_history_requires_auth(client):
    """GET /api/alerts/history without JWT returns 401."""
    resp = client.get("/api/alerts/history")
    assert resp.status_code in (401, 403)


def test_unsubscribe_requires_auth(client):
    """DELETE /api/alerts/unsubscribe/1 without JWT returns 401."""
    resp = client.delete("/api/alerts/unsubscribe/1")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Invalid phone format → 422 (Pydantic field validator)
# ---------------------------------------------------------------------------

def test_subscribe_invalid_phone_format(client, auth_headers):
    """Invalid phone format (not E.164) returns 422."""
    payload = {**_VALID_SUBSCRIBE, "phone": "not-a-phone"}
    resp = client.post(
        "/api/alerts/subscribe",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 422, (
        f"Expected 422 for invalid phone, got {resp.status_code}: {resp.text}"
    )


def test_subscribe_invalid_phone_too_short(client, auth_headers):
    """Phone that's too short returns 422."""
    payload = {**_VALID_SUBSCRIBE, "phone": "+91123"}
    resp = client.post(
        "/api/alerts/subscribe",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 422, (
        f"Expected 422 for too-short phone, got {resp.status_code}: {resp.text}"
    )
