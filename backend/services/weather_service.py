"""
Weather Service — Defensive Titanium implementation.
OpenWeatherMap client with background caching, exponential backoff, and timeout handling.
"""

import time
import httpx
from backend.config import get_settings


class WeatherService:
    """
    Background-cached weather data with exponential backoff.
    Cache TTL: 5 minutes for current, 30 minutes for forecast.
    """

    def __init__(self):
        self._cache: dict[str, tuple[float, dict]] = {}
        self._settings = get_settings()

    def _get_cached(self, key: str, ttl: int) -> dict | None:
        """Return cached value if within TTL, else None."""
        if key in self._cache:
            ts, data = self._cache[key]
            if time.time() - ts < ttl:
                return data
        return None

    async def _fetch_with_backoff(self, url: str) -> dict | None:
        """Fetch URL with exponential backoff on failure."""
        for attempt in range(self._settings.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.get(url)
                    if r.status_code == 200:
                        return r.json()
            except (httpx.TimeoutException, httpx.ConnectError):
                pass
            # Exponential backoff
            await _async_sleep(self._settings.RETRY_BACKOFF_BASE * (2 ** attempt))
        return None

    async def get_current(self, city: str) -> dict | None:
        """Get current weather for a city. Returns cached if available."""
        cache_key = f"weather:current:{city.lower()}"
        if cached := self._get_cached(cache_key, self._settings.WEATHER_CACHE_TTL):
            return cached

        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?q={city},IN&appid={self._settings.OWM_API_KEY}&units=metric"
        )
        data = await self._fetch_with_backoff(url)
        if data and data.get('cod') == 200:
            result = {
                'temp': data['main']['temp'],
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'].title(),
                'wind_speed': round(data['wind']['speed'] * 3.6, 1),
                'rainfall': data.get('rain', {}).get('1h', 0),
                'city': data['name'],
                'lat': data['coord']['lat'],
                'lon': data['coord']['lon'],
                'feels_like': data['main']['feels_like'],
            }
            self._cache[cache_key] = (time.time(), result)
            return result
        return None

    async def get_forecast_rain(self, lat: float, lon: float) -> dict | None:
        """Get 48-hour rainfall forecast for flood risk."""
        cache_key = f"weather:rain:{lat:.2f}:{lon:.2f}"
        if cached := self._get_cached(cache_key, self._settings.FORECAST_CACHE_TTL):
            return cached

        url = (
            f"http://api.openweathermap.org/data/2.5/forecast"
            f"?lat={lat}&lon={lon}&appid={self._settings.OWM_API_KEY}"
            f"&units=metric&cnt=8"
        )
        data = await self._fetch_with_backoff(url)
        if data:
            rain_next48 = sum(
                item.get('rain', {}).get('3h', 0)
                for item in data.get('list', [])
            )
            result = {
                'rain_48h': round(rain_next48, 1),
                'flood_risk': 'HIGH' if rain_next48 > 50 else 'MEDIUM' if rain_next48 > 25 else 'LOW',
            }
            self._cache[cache_key] = (time.time(), result)
            return result
        return None

    async def get_aqi(self, lat: float, lon: float) -> dict | None:
        """Get Air Quality Index."""
        cache_key = f"aqi:{lat:.2f}:{lon:.2f}"
        if cached := self._get_cached(cache_key, self._settings.WEATHER_CACHE_TTL):
            return cached

        url = (
            f"http://api.openweathermap.org/data/2.5/air_pollution"
            f"?lat={lat}&lon={lon}&appid={self._settings.OWM_API_KEY}"
        )
        data = await self._fetch_with_backoff(url)
        if data:
            try:
                aqi_val = data['list'][0]['main']['aqi']
                labels = {1: 'Good', 2: 'Fair', 3: 'Moderate', 4: 'Poor', 5: 'Very Poor'}
                result = {'value': aqi_val, 'label': labels.get(aqi_val, 'Unknown')}
                self._cache[cache_key] = (time.time(), result)
                return result
            except (KeyError, IndexError):
                pass
        return None


async def _async_sleep(seconds: float):
    """Async sleep helper."""
    import asyncio
    await asyncio.sleep(seconds)


# Singleton instance
_weather_service: WeatherService | None = None


def get_weather_service() -> WeatherService:
    """Get or create singleton WeatherService."""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service
