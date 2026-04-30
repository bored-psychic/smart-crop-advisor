from fastapi import APIRouter, HTTPException
from services.weather import WeatherService
from api.schemas import WeatherResponse, FieldWatchResponse
from core.cache import cache_response
from core.config import settings

router = APIRouter()

@router.get("/current/{city}", response_model=WeatherResponse)
@cache_response(ttl=settings.CACHE_TTL_WEATHER, key_prefix="weather_api")
async def get_current_weather(city: str):
    data = await WeatherService.get_weather(city)
    if not data:
        raise HTTPException(status_code=404, detail="City not found or API error")
    return data

@router.get("/field-watch/{city}", response_model=FieldWatchResponse)
@cache_response(ttl=settings.CACHE_TTL_WEATHER, key_prefix="field_watch_api")
async def get_field_watch(city: str):
    data = await WeatherService.fetch_field_watch(city)
    return data
