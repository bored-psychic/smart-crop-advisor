"""
FAO Desert Locust Service — Defensive data ingestion.
"""

import time
import httpx
from backend.config import get_settings


class LocustService:
    """FAO Desert Locust Hub client with caching."""

    def __init__(self):
        self._cache: dict[str, tuple[float, dict]] = {}
        self._settings = get_settings()

    async def get_swarms(self, lat: float, lon: float) -> dict:
        """Check for nearby locust swarms."""
        cache_key = f"locust:{lat:.1f}:{lon:.1f}"
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if time.time() - ts < self._settings.FIRMS_CACHE_TTL:
                return data

        try:
            url = "https://locust-hub-hqfao.hub.arcgis.com/datasets/fao::desert-locust-presence-1.geojson"
            async with httpx.AsyncClient(timeout=6.0) as client:
                r = await client.get(url)

            if r.status_code == 200:
                gjson = r.json()
                features = gjson.get('features', [])
                nearby = 0
                for feat in features[:200]:
                    coords = feat.get('geometry', {}).get('coordinates', [])
                    if coords:
                        flon, flat = coords[0], coords[1]
                        if (flat - lat) ** 2 + (flon - lon) ** 2 < 25.0:  # 5° radius
                            nearby += 1

                result = {
                    'swarms_nearby': nearby,
                    'risk': 'HIGH' if nearby > 2 else 'MEDIUM' if nearby > 0 else 'NONE',
                    'source': 'FAO Desert Locust Hub',
                }
                self._cache[cache_key] = (time.time(), result)
                return result
        except Exception:
            pass

        return {'swarms_nearby': 0, 'risk': 'UNKNOWN', 'source': 'FAO Hub (unavailable)'}


_locust_service: LocustService | None = None


def get_locust_service() -> LocustService:
    global _locust_service
    if _locust_service is None:
        _locust_service = LocustService()
    return _locust_service
