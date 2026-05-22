"""Tests for the crop recommendation router (/api/crop/recommend).

Verifies that the Random-Forest-based endpoint returns valid predictions
for well-formed input and rejects invalid inputs with appropriate HTTP
status codes.
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
    "N": 80,
    "P": 40,
    "K": 40,
    "temperature": 25.0,
    "humidity": 65.0,
    "ph": 6.5,
    "rainfall": 100.0,
}


# ---------------------------------------------------------------------------
# Happy path: valid inputs → 200 with top-N crops
# ---------------------------------------------------------------------------

def test_crop_recommend_happy_path(client, auth_headers):
    """Valid soil/climate inputs return 200 with crop recommendations."""
    resp = client.post(
        "/api/crop/recommend",
        json=_VALID_PAYLOAD,
        headers=auth_headers,
    )

    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert "top_crop" in data
    assert "alternatives" in data
    assert isinstance(data["alternatives"], list)
    assert "tip" in data
    assert "soil" in data
    # top_crop must include a crop name and confidence
    top = data["top_crop"]
    assert "crop" in top
    assert "confidence" in top
    # Confidence may be 0.0–1.0 (fraction) or 0–100 (percentage) depending
    # on model output; just check it's a non-negative number.
    assert top["confidence"] >= 0


# ---------------------------------------------------------------------------
# pH too high → 422 (pydantic range validator)
# ---------------------------------------------------------------------------

def test_crop_recommend_invalid_ph_too_high(client, auth_headers):
    """pH exceeding the allowed maximum (9.5) returns 422."""
    payload = {**_VALID_PAYLOAD, "ph": 99}
    resp = client.post(
        "/api/crop/recommend",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 422, (
        f"Expected 422 for pH=99, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# pH negative → 422
# ---------------------------------------------------------------------------

def test_crop_recommend_invalid_ph_negative(client, auth_headers):
    """Negative pH returns 422."""
    payload = {**_VALID_PAYLOAD, "ph": -1}
    resp = client.post(
        "/api/crop/recommend",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 422, (
        f"Expected 422 for pH=-1, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Missing required field → 422
# ---------------------------------------------------------------------------

def test_crop_recommend_missing_field(client, auth_headers):
    """Missing required field `N` returns 422."""
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "N"}
    resp = client.post(
        "/api/crop/recommend",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 422, (
        f"Expected 422 for missing N, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Auth check
# ---------------------------------------------------------------------------

def test_crop_recommend_requires_auth(client):
    """Endpoint rejects requests without an Authorization header."""
    resp = client.post("/api/crop/recommend", json=_VALID_PAYLOAD)
    assert resp.status_code in (401, 403)
