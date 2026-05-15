"""Field Watch router — satellite intelligence scan."""

import asyncio
from fastapi import APIRouter, Depends
from backend.schemas.field_watch import (
    FieldWatchRequest, FieldWatchResponse,
    WeatherInfo, FloodAlert, FireAlert, LocustAlert, AQIInfo,
)
from backend.services.weather_service import get_weather_service
from backend.services.firms_service import get_firms_service
from backend.services.locust_service import get_locust_service
from backend.auth import require_api_key

router = APIRouter(prefix="/api/field-watch", tags=["Field Watch"])


@router.post("/scan", response_model=FieldWatchResponse)
async def scan_field(
    req: FieldWatchRequest,
    _: str = Depends(require_api_key),
):
    """
    Aggregate satellite intelligence:
    1. OpenWeatherMap current + forecast
    2. NASA FIRMS wildfire hotspots
    3. FAO Desert Locust swarms
    4. Air Quality Index
    """
    weather_svc = get_weather_service()
    firms_svc = get_firms_service()
    locust_svc = get_locust_service()

    # 1. Current weather
    weather_data = await weather_svc.get_current(req.city)
    weather = None
    lat, lon = None, None

    if weather_data:
        lat = weather_data['lat']
        lon = weather_data['lon']
        weather = WeatherInfo(
            temp=weather_data['temp'],
            feels_like=weather_data['feels_like'],
            humidity=weather_data['humidity'],
            wind=weather_data['wind_speed'],
            description=weather_data['description'],
            rain_1h=weather_data['rainfall'],
            lat=lat,
            lon=lon,
        )

    # 2-5. Fan out flood/fire/locust/aqi concurrently — these are independent.
    flood = fire = locust = aqi = None
    if lat and lon:
        flood_data, fire_data, locust_data, aqi_data = await asyncio.gather(
            weather_svc.get_forecast_rain(lat, lon),
            firms_svc.get_hotspots(lat, lon),
            locust_svc.get_swarms(lat, lon),
            weather_svc.get_aqi(lat, lon),
            return_exceptions=True,
        )
        if isinstance(flood_data, dict):
            flood = FloodAlert(**flood_data)
        if isinstance(fire_data, dict):
            fire = FireAlert(
                hotspots_nearby=fire_data['hotspots_nearby'],
                risk=fire_data['risk'],
                source=fire_data['source'],
            )
        if isinstance(locust_data, dict):
            locust = LocustAlert(**locust_data)
        if isinstance(aqi_data, dict):
            aqi = AQIInfo(**aqi_data)

    # Overall risk
    risks = [
        fire.risk if fire else 'NONE',
        flood.flood_risk if flood else 'LOW',
        locust.risk if locust else 'NONE',
    ]
    if 'HIGH' in risks:
        overall = 'HIGH'
    elif 'MEDIUM' in risks:
        overall = 'MEDIUM'
    else:
        overall = 'LOW'

    return FieldWatchResponse(
        city=req.city,
        overall_risk=overall,
        weather=weather,
        flood=flood,
        fire=fire,
        locust=locust,
        aqi=aqi,
    )
