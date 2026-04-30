import httpx
import streamlit as st

BACKEND_URL = "http://localhost:8000/api/v1"

class APIClient:
    @staticmethod
    async def get_weather(city: str):
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BACKEND_URL}/weather/current/{city}")
            return r.json() if r.status_code == 200 else None

    @staticmethod
    async def recommend_crop(data: dict):
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{BACKEND_URL}/crop/recommend", json=data)
            return r.json() if r.status_code == 200 else None

    @staticmethod
    async def get_market_price(state: str, crop: str):
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BACKEND_URL}/market/price/{state}/{crop}")
            return r.json() if r.status_code == 200 else None

    @staticmethod
    async def diagnose_vision(image_bytes: bytes):
        async with httpx.AsyncClient() as client:
            files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
            r = await client.post(f"{BACKEND_URL}/vision/diagnose", files=files)
            return r.json() if r.status_code == 200 else None

    @staticmethod
    async def analyze_acoustic(audio_bytes: bytes):
        async with httpx.AsyncClient() as client:
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            r = await client.post(f"{BACKEND_URL}/acoustic/analyze", files=files)
            return r.json() if r.status_code == 200 else None

    @staticmethod
    async def get_field_watch(city: str):
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BACKEND_URL}/weather/field-watch/{city}")
            return r.json() if r.status_code == 200 else None
