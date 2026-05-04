import os
import httpx
import streamlit as st

_BACKEND_DEFAULT = "http://localhost:8000/api"


def _backend_url() -> str:
    try:
        return st.secrets.get("BACKEND_URL", "") or os.environ.get("BACKEND_URL", _BACKEND_DEFAULT)
    except Exception:
        return os.environ.get("BACKEND_URL", _BACKEND_DEFAULT)


def _api_key() -> str:
    try:
        return st.secrets.get("BACKEND_API_KEY", "") or os.environ.get("BACKEND_API_KEY", "kisanos-dev-key-change-in-production")
    except Exception:
        return os.environ.get("BACKEND_API_KEY", "kisanos-dev-key-change-in-production")


def _headers() -> dict:
    return {"X-API-Key": _api_key()}


class APIClient:
    @staticmethod
    async def get_weather(city: str):
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{_backend_url()}/field-watch/scan",
                json={"city": city},
                headers=_headers(),
            )
            if r.status_code == 200:
                body = r.json()
                w = body.get("weather") or {}
                return {
                    "temp":        w.get("temp"),
                    "humidity":    w.get("humidity"),
                    "wind_speed":  w.get("wind"),
                    "rainfall":    w.get("rain_1h", 0),
                    "city":        body.get("city", city),
                    "description": w.get("description", ""),
                }
            return None

    @staticmethod
    async def recommend_crop(data: dict):
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{_backend_url()}/crop/recommend",
                json=data,
                headers=_headers(),
            )
            return r.json() if r.status_code == 200 else None

    @staticmethod
    async def get_market_price(state: str, crop: str, forecast_days: int = 30):
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{_backend_url()}/market/forecast",
                json={"crop": crop, "state": state, "forecast_days": forecast_days},
                headers=_headers(),
            )
            return r.json() if r.status_code == 200 else None

    @staticmethod
    async def diagnose_vision(image_bytes: bytes, crop_type: str = "Unknown"):
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                f"{_backend_url()}/disease/analyze-image",
                files={"file": ("image.jpg", image_bytes, "image/jpeg")},
                data={"crop_type": crop_type},
                headers=_headers(),
            )
            return r.json() if r.status_code == 200 else None

    @staticmethod
    async def analyze_acoustic(audio_bytes: bytes, crop_type: str = "Unknown"):
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                f"{_backend_url()}/acoustic/analyze",
                files={"file": ("audio.wav", audio_bytes, "audio/wav")},
                data={"crop_type": crop_type},
                headers=_headers(),
            )
            return r.json() if r.status_code == 200 else None

    @staticmethod
    async def get_field_watch(city: str):
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{_backend_url()}/field-watch/scan",
                json={"city": city},
                headers=_headers(),
            )
            return r.json() if r.status_code == 200 else None
