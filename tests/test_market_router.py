"""Tests for the market price + forecast router (/api/market/forecast).

Uses respx to mock Agmarknet and weather geocoding calls so no real
network traffic is generated.
"""
from __future__ import annotations

import pytest
import respx
import httpx
from fastapi.testclient import TestClient

from backend.main import app

pytest.importorskip("respx", reason="respx not installed; skipping market router tests")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# Agmarknet data.gov.in URL pattern
_AGMARKNET_PATTERN = r"api\.data\.gov\.in"
# OpenWeatherMap geocoding URL pattern
_OWM_GEO_PATTERN = r"api\.openweathermap\.org"


def _agmarknet_response():
    """Minimal Agmarknet JSON with a single price record."""
    return {
        "records": [
            {
                "state": "Karnataka",
                "district": "Bangalore",
                "market": "Bangalore",
                "commodity": "Rice",
                "min_price": "1800",
                "max_price": "2200",
                "modal_price": "2000",
                "arrival_date": "22/05/2026",
            }
        ]
    }


def _geocode_response():
    """Minimal OWM geocoding response for Bangalore → Karnataka."""
    return [{"name": "Bangalore", "state": "Karnataka", "country": "IN",
             "lat": 12.97, "lon": 77.59}]


# ---------------------------------------------------------------------------
# Happy path: POST /api/market/forecast returns 200 with price data
# ---------------------------------------------------------------------------

@respx.mock
def test_market_forecast_happy_path(client, auth_headers):
    """When Agmarknet returns price data, the endpoint returns 200."""
    # Mock the geocoding call so resolve_city_state works.
    respx.get(url__regex=_OWM_GEO_PATTERN).mock(
        return_value=httpx.Response(200, json=_geocode_response())
    )
    # Mock the Agmarknet call with a valid record.
    respx.get(url__regex=_AGMARKNET_PATTERN).mock(
        return_value=httpx.Response(200, json=_agmarknet_response())
    )

    resp = client.post(
        "/api/market/forecast",
        json={"crop": "Rice", "city": "Bangalore", "forecast_days": 7},
        headers=auth_headers,
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["crop"] == "Rice"
    assert data["state"] == "Karnataka"
    assert data["city"] == "Bangalore"


# ---------------------------------------------------------------------------
# 503 when Agmarknet times out
# ---------------------------------------------------------------------------

@respx.mock
def test_market_forecast_agmarknet_timeout(client, auth_headers):
    """When Agmarknet times out, the endpoint degrades gracefully (no crash).

    The MarketService may return a cached result from a prior test run, or
    None on a fresh call. Either way the endpoint must return 200 (not 5xx).
    """
    respx.get(url__regex=_OWM_GEO_PATTERN).mock(
        return_value=httpx.Response(200, json=_geocode_response())
    )
    # Simulate a connect timeout on Agmarknet.
    respx.get(url__regex=_AGMARKNET_PATTERN).mock(
        side_effect=httpx.ConnectTimeout("Connection timed out")
    )

    resp = client.post(
        "/api/market/forecast",
        # Use a different crop to avoid the module-scoped MarketService cache
        # from the happy-path test — Maize has a separate cache key.
        json={"crop": "Maize", "city": "Bangalore", "forecast_days": 7},
        headers=auth_headers,
    )

    # The router must not 5xx — it degrades gracefully.
    assert resp.status_code not in (500, 503), (
        f"Endpoint should degrade gracefully on Agmarknet timeout, "
        f"got {resp.status_code}: {resp.text}"
    )
    assert resp.status_code == 200, (
        f"Expected 200 (with null live_price on timeout), got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    # live_price must be null when Agmarknet timed out and the cache is empty.
    assert data.get("live_price") is None, (
        f"Expected live_price=null on Agmarknet timeout, got: {data.get('live_price')}"
    )


# ---------------------------------------------------------------------------
# Auth check: 401 without JWT
# ---------------------------------------------------------------------------

def test_market_forecast_requires_auth(client):
    """Endpoint rejects requests without an Authorization header."""
    resp = client.post(
        "/api/market/forecast",
        json={"crop": "Rice", "city": "Bangalore", "forecast_days": 7},
    )
    assert resp.status_code in (401, 403)
