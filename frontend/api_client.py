import os
import asyncio
import threading
import httpx
import streamlit as st

_BACKEND_DEFAULT = "http://localhost:8000/api"
_DEFAULT_TIMEOUT = httpx.Timeout(20.0, connect=3.0)


def run_async(coro):
    """Safely run async code in Streamlit context.
    Avoids RuntimeError: asyncio.run() cannot be called from a running event loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result = {}

    def _runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result['value'] = loop.run_until_complete(coro)
        except Exception as exc:
            result['error'] = exc
        finally:
            loop.close()

    thread = threading.Thread(target=_runner)
    thread.start()
    thread.join()

    if 'error' in result:
        raise result['error']
    return result.get('value')


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


async def _post_json(path: str, **kwargs) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=kwargs.pop("timeout", _DEFAULT_TIMEOUT)) as client:
            r = await client.post(
                f"{_backend_url()}{path}",
                headers=_headers(),
                **kwargs,
            )
            return r.json() if r.status_code == 200 else None
    except Exception:
        return None


class APIClient:
    @staticmethod
    async def get_weather(city: str):
        body = await _post_json(
            "/field-watch/scan",
            json={"city": city},
            timeout=httpx.Timeout(20.0, connect=3.0),
        )
        if not body:
            return None
        w = body.get("weather") or {}
        return {
            "temp":        w.get("temp"),
            "humidity":    w.get("humidity"),
            "wind_speed":  w.get("wind"),
            "rainfall":    w.get("rain_1h", 0),
            "city":        body.get("city", city),
            "description": w.get("description", ""),
        }

    @staticmethod
    async def recommend_crop(data: dict):
        return await _post_json("/crop/recommend", json=data)

    @staticmethod
    async def get_market_price(city: str, crop: str, forecast_days: int = 30):
        return await _post_json(
            "/market/forecast",
            json={"crop": crop, "city": city, "forecast_days": forecast_days},
            timeout=httpx.Timeout(30.0, connect=3.0),
        )

    @staticmethod
    async def diagnose_vision(image_bytes: bytes, crop_type: str = "Unknown"):
        return await _post_json(
            "/disease/analyze-image",
            files={"file": ("image.jpg", image_bytes, "image/jpeg")},
            timeout=httpx.Timeout(45.0, connect=5.0),
        )

    @staticmethod
    async def analyze_acoustic(audio_bytes: bytes, crop_type: str = "Unknown"):
        return await _post_json(
            "/acoustic/analyze",
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"crop_type": crop_type},
            timeout=httpx.Timeout(45.0, connect=5.0),
        )

    @staticmethod
    async def irrigation_advice(data: dict):
        return await _post_json(
            "/irrigation/advise",
            json=data,
            timeout=httpx.Timeout(15.0, connect=3.0),
        )

    @staticmethod
    async def diagnose_symptom(crop: str, symptom: str):
        return await _post_json(
            "/disease/analyze-symptom",
            json={"crop": crop, "symptom": symptom},
            timeout=httpx.Timeout(15.0, connect=3.0),
        )

    @staticmethod
    async def get_field_watch(city: str):
        return await _post_json(
            "/field-watch/scan",
            json={"city": city},
            timeout=httpx.Timeout(20.0, connect=3.0),
        )
