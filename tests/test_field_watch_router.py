"""Resilience tests for /api/field-watch/scan.

Verifies that the scan endpoint degrades gracefully when individual
upstream APIs (weather, fire, locust) fail.

Uses `respx` to intercept httpx calls at the transport level.
"""
from __future__ import annotations

import pytest
import respx
import httpx
from fastapi.testclient import TestClient

from backend.main import app

pytest.importorskip("respx", reason="respx not installed; skipping field-watch tests")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


_OWM_PATTERN = r"api\.openweathermap\.org"
_FIRMS_PATTERN = r"firms\.modaps\.eosdis\.nasa\.gov"
_FAO_PATTERN = r"locust-hub-hqfao\.hub\.arcgis\.com"


def _weather_200():
    """Minimal OWM current-weather response with lat/lon.

    Must include `cod: 200` so WeatherService._fetch_with_backoff's
    `data.get('cod') == 200` check passes and returns a result dict.
    """
    return {
        "cod": 200,
        "name": "Mumbai",
        "coord": {"lat": 19.07, "lon": 72.88},
        "main": {"temp": 28.0, "feels_like": 30.0, "humidity": 75},
        "wind": {"speed": 3.5},
        "weather": [{"description": "partly cloudy"}],
        "rain": {},
    }


# ---------------------------------------------------------------------------
# When weather API returns 502: endpoint still returns 200, weather=null
# ---------------------------------------------------------------------------

@respx.mock
def test_field_watch_returns_200_when_weather_502(client, auth_headers):
    """When OWM returns 502, the scan endpoint degrades — weather=null, status=200."""
    respx.get(url__regex=_OWM_PATTERN).mock(
        return_value=httpx.Response(502, text="Bad Gateway")
    )
    # FIRMS and FAO don't matter when there's no lat/lon from weather.
    respx.get(url__regex=_FIRMS_PATTERN).mock(
        return_value=httpx.Response(200, text="latitude,longitude\n")
    )
    respx.get(url__regex=_FAO_PATTERN).mock(
        return_value=httpx.Response(200, json={"features": []})
    )

    resp = client.post(
        "/api/field-watch/scan",
        json={"city": "Mumbai"},
        headers=auth_headers,
    )

    assert resp.status_code == 200, (
        f"Expected 200 on OWM 502, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data.get("weather") is None, (
        f"Expected weather=null on OWM 502, got: {data.get('weather')}"
    )


# ---------------------------------------------------------------------------
# When fire API (FIRMS) times out: endpoint still returns 200 with partial data
# ---------------------------------------------------------------------------

@respx.mock
def test_field_watch_returns_200_when_fire_timeout(client, auth_headers):
    """When FIRMS times out, scan still returns 200 (fire=null or empty list)."""
    respx.get(url__regex=_OWM_PATTERN).mock(
        return_value=httpx.Response(200, json=_weather_200())
    )
    respx.get(url__regex=_FIRMS_PATTERN).mock(
        side_effect=httpx.ConnectTimeout("FIRMS timed out")
    )
    respx.get(url__regex=_FAO_PATTERN).mock(
        return_value=httpx.Response(200, json={"features": []})
    )

    resp = client.post(
        "/api/field-watch/scan",
        json={"city": "Mumbai"},
        headers=auth_headers,
    )

    assert resp.status_code == 200, (
        f"Expected 200 on FIRMS timeout, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    # Weather should be present (OWM succeeded).
    assert data.get("weather") is not None, "Expected weather data when OWM succeeds"
    # Fire should be None or an empty-alert structure — not an unhandled exception.
    fire = data.get("fire")
    assert fire is None or isinstance(fire, dict), (
        f"Expected fire=null or dict on FIRMS timeout, got: {fire}"
    )


# ---------------------------------------------------------------------------
# When locust API fails: endpoint still returns 200 with partial data
# ---------------------------------------------------------------------------

@respx.mock
def test_field_watch_returns_200_when_locust_fails(client, auth_headers):
    """When the FAO locust API returns 500, scan still returns 200."""
    respx.get(url__regex=_OWM_PATTERN).mock(
        return_value=httpx.Response(200, json=_weather_200())
    )
    respx.get(url__regex=_FIRMS_PATTERN).mock(
        return_value=httpx.Response(200, text="latitude,longitude\n")
    )
    respx.get(url__regex=_FAO_PATTERN).mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    resp = client.post(
        "/api/field-watch/scan",
        json={"city": "Mumbai"},
        headers=auth_headers,
    )

    assert resp.status_code == 200, (
        f"Expected 200 on locust API failure, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data.get("weather") is not None


# ---------------------------------------------------------------------------
# Auth check
# ---------------------------------------------------------------------------

def test_field_watch_requires_auth(client):
    """Endpoint rejects requests without an Authorization header."""
    resp = client.post("/api/field-watch/scan", json={"city": "Mumbai"})
    assert resp.status_code in (401, 403)
