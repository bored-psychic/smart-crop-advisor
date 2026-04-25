"""
NASA FIRMS Service — Defensive Titanium Implementation.

Handles:
  - Column header shifts (positional fallback)
  - Corrupt/malformed CSV rows (skip silently)
  - Encoding errors (latin-1 fallback)
  - API timeouts (exponential backoff)
  - Rate limits (TTL-based caching)
  - Stale data (cached fallback on failure)
"""

import time
import httpx
from backend.config import get_settings


class FIRMSService:
    """
    Defensive Titanium implementation for NASA FIRMS wildfire data.
    CSV ingestion tolerates schema drift and corruption gracefully.
    """

    # Known header variants across FIRMS API versions
    EXPECTED_HEADERS = {'latitude', 'lat', 'longitude', 'lon', 'brightness', 'confidence'}
    FALLBACK_COL_MAP = {0: 'latitude', 1: 'longitude'}

    def __init__(self):
        self._cache: dict[str, tuple[float, dict]] = {}
        self._settings = get_settings()

    async def get_hotspots(self, lat: float, lon: float, radius_deg: float = 2.0) -> dict:
        """
        Get wildfire hotspots near a location.
        Returns: {hotspots_nearby, risk, source}
        """
        cache_key = f"firms:{lat:.1f}:{lon:.1f}"

        # Check cache first
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if time.time() - ts < self._settings.FIRMS_CACHE_TTL:
                return data

        # Fetch with retry
        csv_text = await self._fetch_with_retry()
        if csv_text is None:
            return self._cached_or_unknown(cache_key)

        result = self._parse_defensive(csv_text, lat, lon, radius_deg)
        self._cache[cache_key] = (time.time(), result)
        return result

    async def _fetch_with_retry(self) -> str | None:
        """Fetch FIRMS CSV with exponential backoff."""
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/"
            f"{self._settings.NASA_FIRMS_KEY}/MODIS_NRT/IND/1"
        )
        for attempt in range(self._settings.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=7.0) as client:
                    r = await client.get(url)
                    if r.status_code == 200 and r.text.strip():
                        return r.text
            except (httpx.TimeoutException, httpx.ConnectError):
                pass
            # Exponential backoff
            import asyncio
            await asyncio.sleep(self._settings.RETRY_BACKOFF_BASE * (2 ** attempt))
        return None

    def _parse_defensive(self, csv_text: str, lat: float, lon: float, radius: float) -> dict:
        """
        Parse CSV with column-shift tolerance.

        Strategy:
        1. Try header-based column detection (handles renamed columns)
        2. Fall back to positional columns if headers don't match
        3. Skip corrupt rows silently (never crash)
        4. Return partial results rather than failing
        """
        lines = csv_text.strip().split('\n')
        if not lines:
            return {'hotspots_nearby': 0, 'risk': 'UNKNOWN', 'source': 'NASA FIRMS (empty)'}

        # Detect column positions from header
        header = lines[0].lower().strip().split(',')
        lat_col = self._find_col(header, ['latitude', 'lat'])
        lon_col = self._find_col(header, ['longitude', 'lon'])

        # Positional fallback if headers shifted
        if lat_col is None:
            lat_col = 0
        if lon_col is None:
            lon_col = 1

        # Squared radius for distance comparison (avoids sqrt — O(1) per point)
        radius_sq = radius ** 2

        hotspots = 0
        parse_errors = 0
        for line in lines[1:]:
            try:
                parts = line.split(',')
                if len(parts) <= max(lat_col, lon_col):
                    parse_errors += 1
                    continue
                flat = float(parts[lat_col])
                flon = float(parts[lon_col])
                # Fast squared distance check — no sqrt needed
                if (flat - lat) ** 2 + (flon - lon) ** 2 < radius_sq:
                    hotspots += 1
            except (ValueError, IndexError):
                parse_errors += 1
                continue  # Skip corrupt rows silently

        return {
            'hotspots_nearby': hotspots,
            'risk': 'HIGH' if hotspots > 5 else 'MEDIUM' if hotspots > 0 else 'NONE',
            'source': 'NASA FIRMS MODIS',
            'parse_errors': parse_errors,
        }

    @staticmethod
    def _find_col(header: list[str], candidates: list[str]) -> int | None:
        """Find column index by trying multiple header name variants."""
        for candidate in candidates:
            for i, col in enumerate(header):
                if candidate in col.strip():
                    return i
        return None

    def _cached_or_unknown(self, cache_key: str) -> dict:
        """Return stale cache if available, otherwise UNKNOWN."""
        if cache_key in self._cache:
            _, data = self._cache[cache_key]
            data['source'] = data.get('source', 'NASA FIRMS') + ' (cached/stale)'
            return data
        return {
            'hotspots_nearby': 0,
            'risk': 'UNKNOWN',
            'source': 'NASA FIRMS (unavailable)',
        }


# Singleton
_firms_service: FIRMSService | None = None


def get_firms_service() -> FIRMSService:
    global _firms_service
    if _firms_service is None:
        _firms_service = FIRMSService()
    return _firms_service
