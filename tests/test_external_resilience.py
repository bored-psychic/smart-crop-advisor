"""
Resilience tests: external HTTP failure handling.

Verifies that the field-watch and market-service endpoints degrade
gracefully when upstream APIs return 5xx errors or time out, rather
than propagating unhandled exceptions to callers.

Uses `respx` to intercept `httpx` calls at the transport level so
no real network traffic is generated.
"""
from __future__ import annotations

import logging
import pytest

pytest.importorskip("respx", reason="respx not installed; skipping resilience tests")

import httpx
import respx
from fastapi.testclient import TestClient

from backend.main import app


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    """TestClient wrapping the full FastAPI application."""
    with TestClient(app) as c:
        yield c


# ── helpers ───────────────────────────────────────────────────────────────────

_OWM_PATTERN = r"api\.openweathermap\.org"
_AGMARKNET_PATTERN = r"api\.data\.gov\.in"
_FIRMS_PATTERN = r"firms\.modaps\.eosdis\.nasa\.gov"
_FAO_PATTERN = r"locust-hub-hqfao\.hub\.arcgis\.com"


# ── weather 502 → field-watch returns HTTP 200 with weather=null ──────────────


@respx.mock
def test_field_watch_returns_200_when_owm_502(client, auth_headers):
    """
    When OpenWeatherMap returns 502, the field-watch scan endpoint must:
    - still respond with HTTP 200 (graceful degradation)
    - include `weather: null` in the response body (unavailable sentinel)
    """
    # Intercept all OWM HTTP calls and return 502.
    respx.get(url__regex=_OWM_PATTERN).mock(
        return_value=httpx.Response(502, text="Bad Gateway")
    )
    # Also stub out FIRMS and FAO so the rest of the scan doesn't hang.
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
        f"Expected 200 on upstream failure, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    # Weather is null/None when the upstream is unavailable.
    assert data.get("weather") is None, (
        f"Expected weather=null on OWM 502, got: {data.get('weather')}"
    )


# ── weather service logs warning on 502 (direct call, no TestClient) ──────────


@respx.mock
def test_weather_service_logs_warning_on_owm_502(caplog):
    """
    WeatherService._fetch_with_backoff must emit a WARNING when OWM
    returns 502, not swallow the status error silently.
    Direct service call — avoids async-log propagation issues in TestClient.
    """
    import asyncio
    from backend.services.weather_service import WeatherService

    respx.get(url__regex=_OWM_PATTERN).mock(
        return_value=httpx.Response(502, text="Bad Gateway")
    )

    svc = WeatherService()
    svc._settings.MAX_RETRIES = 1  # Single attempt so the test is fast.

    with caplog.at_level(logging.WARNING, logger="backend.services.weather_service"):
        result = asyncio.run(
            svc.get_current("Mumbai")
        )

    assert result is None, f"Expected None on OWM 502, got: {result}"
    warning_records = [
        r for r in caplog.records
        if r.levelno >= logging.WARNING
        and "weather_service" in (r.name or "").lower()
    ]
    assert warning_records, (
        "Expected a WARNING log when OWM returns 502, but none were emitted."
    )


# ── market service timeout → get_live_price returns None ──────────────────────


@respx.mock
def test_market_service_returns_none_on_timeout(caplog):
    """
    When Agmarknet times out, MarketService.get_live_price must:
    - return None (not raise)
    - emit a WARNING-level log entry
    """
    import asyncio
    from backend.services.market_service import MarketService

    # Simulate a connect timeout on every Agmarknet request.
    respx.get(url__regex=_AGMARKNET_PATTERN).mock(
        side_effect=httpx.ConnectTimeout("Connection timed out")
    )

    svc = MarketService()

    with caplog.at_level(logging.WARNING, logger="backend.services.market_service"):
        result = asyncio.run(
            svc.get_live_price("Rice", "Karnataka")
        )

    assert result is None, (
        f"Expected None when Agmarknet times out, got: {result}"
    )
    warning_records = [
        r for r in caplog.records
        if r.levelno >= logging.WARNING
        and "market_service" in (r.name or "").lower()
    ]
    assert warning_records, (
        "Expected a WARNING log when Agmarknet times out, but none were emitted."
    )


# ── market service 502 → get_live_price returns None ─────────────────────────


@respx.mock
def test_market_service_returns_none_on_502(caplog):
    """
    When Agmarknet returns 502, MarketService.get_live_price must:
    - return None (not raise)
    - emit a WARNING-level log entry
    """
    import asyncio
    from backend.services.market_service import MarketService

    respx.get(url__regex=_AGMARKNET_PATTERN).mock(
        return_value=httpx.Response(502, text="Bad Gateway")
    )

    svc = MarketService()

    with caplog.at_level(logging.WARNING, logger="backend.services.market_service"):
        result = asyncio.run(
            svc.get_live_price("Wheat", "Punjab")
        )

    assert result is None, (
        f"Expected None when Agmarknet returns 502, got: {result}"
    )
    warning_records = [
        r for r in caplog.records
        if r.levelno >= logging.WARNING
        and "market_service" in (r.name or "").lower()
    ]
    assert warning_records, (
        "Expected a WARNING log when Agmarknet returns 502, but none were emitted."
    )


# ── weather service logs warning on upstream failure ─────────────────────────


@respx.mock
def test_weather_service_logs_warning_on_502(caplog):
    """
    WeatherService._fetch_with_backoff must emit a WARNING on each failed
    attempt, not swallow the exception silently.
    """
    import asyncio
    from backend.services.weather_service import WeatherService

    # Return 502 so raise_for_status triggers an HTTPStatusError.
    respx.get(url__regex=_OWM_PATTERN).mock(
        return_value=httpx.Response(502, text="Bad Gateway")
    )

    svc = WeatherService()
    # Patch MAX_RETRIES to 1 so the test is fast.
    svc._settings.MAX_RETRIES = 1

    with caplog.at_level(logging.WARNING, logger="backend.services.weather_service"):
        result = asyncio.run(
            svc.get_current("Chennai")
        )

    assert result is None, f"Expected None on 502, got: {result}"
