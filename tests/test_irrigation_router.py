"""Tests for the irrigation advisor router (/api/irrigation/advise).

Verifies happy paths and validation behaviour. No external HTTP mocking
needed — the irrigation endpoint is purely computational (FAO-56).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


_VALID_PAYLOAD = {
    "crop": "Rice",
    "growth_stage": "Mid-season",
    "field_area": 2.0,
    "last_rain_mm": 5.0,
    "temperature": 32.0,
    "humidity": 70.0,
    "wind_speed": 12.0,
}


# ---------------------------------------------------------------------------
# Happy path: POST with valid soil/crop inputs returns 200
# ---------------------------------------------------------------------------

def test_irrigation_advise_happy_path(client, auth_headers):
    """Valid irrigation request returns 200 with a recommendation."""
    resp = client.post(
        "/api/irrigation/advise",
        json=_VALID_PAYLOAD,
        headers=auth_headers,
    )

    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data["crop"] == "Rice"
    assert "net_irrigation_mm" in data
    assert "advice" in data
    assert "urgency" in data
    assert data["urgency"] in ("none", "light", "urgent")
    assert "fertilizer" in data


# ---------------------------------------------------------------------------
# Invalid crop → 404
# ---------------------------------------------------------------------------

def test_irrigation_advise_unknown_crop(client, auth_headers):
    """Crop not in CROP_KC database returns 404."""
    payload = {**_VALID_PAYLOAD, "crop": "MagicBean"}
    resp = client.post(
        "/api/irrigation/advise",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 404, (
        f"Expected 404 for unknown crop, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Invalid growth stage → 400
# ---------------------------------------------------------------------------

def test_irrigation_advise_invalid_growth_stage(client, auth_headers):
    """Invalid growth stage returns 400."""
    payload = {**_VALID_PAYLOAD, "growth_stage": "InvalidStage"}
    resp = client.post(
        "/api/irrigation/advise",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 400, (
        f"Expected 400 for invalid growth stage, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Missing required fields → 422
# ---------------------------------------------------------------------------

def test_irrigation_advise_missing_crop(client, auth_headers):
    """Missing required field `crop` returns 422."""
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "crop"}
    resp = client.post(
        "/api/irrigation/advise",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 422, (
        f"Expected 422 for missing crop, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Auth check
# ---------------------------------------------------------------------------

def test_irrigation_advise_requires_auth(client):
    """Endpoint rejects requests without an Authorization header."""
    resp = client.post("/api/irrigation/advise", json=_VALID_PAYLOAD)
    assert resp.status_code in (401, 403)
