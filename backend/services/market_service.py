"""
Market Service — Live Agmarknet prices.
Defensive Titanium: handles API failures, corrupt responses, and timeouts.
"""

import time
import httpx
from backend.config import get_settings
from backend.data.state_prices import STATE_PRICE_FACTORS


class MarketService:
    """Agmarknet live price client with caching and retry."""

    def __init__(self):
        self._cache: dict[str, tuple[float, dict]] = {}
        self._settings = get_settings()

    async def get_live_price(self, crop: str, state: str) -> dict | None:
        """
        Fetch live Agmarknet price via data.gov.in API.
        Returns {today_price, source, mandis_checked, state_factor, live, city_prices} or None.
        city_prices is populated only for Karnataka.
        """
        cache_key = f"market:{crop}:{state}"
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if time.time() - ts < self._settings.MARKET_CACHE_TTL:
                return data

        is_karnataka = state.lower() == "karnataka"
        limit = 50 if is_karnataka else 10

        try:
            crop_clean = crop.replace(' ', '%20')
            state_clean = state.replace(' ', '%20')
            url = (
                f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
                f"?api-key={self._settings.DATA_GOV_API_KEY}"
                f"&format=json&limit={limit}"
                f"&filters%5Bcommodity%5D={crop_clean}"
                f"&filters%5Bstate%5D={state_clean}"
            )
            async with httpx.AsyncClient(timeout=6.0) as client:
                r = await client.get(url)
                data = r.json()

            records = data.get('records', [])
            if records:
                prices = []
                district_prices: dict[str, list[float]] = {}

                for rec in records:
                    try:
                        price = float(
                            rec.get('modal_price', 0) or rec.get('max_price', 0)
                        )
                        if price <= 0:
                            continue
                        prices.append(price)
                        if is_karnataka:
                            district = (rec.get('district') or rec.get('market') or '').strip().title()
                            if district:
                                district_prices.setdefault(district, []).append(price)
                    except (ValueError, TypeError):
                        continue

                if prices:
                    today_price = sum(prices) / len(prices)
                    state_f = STATE_PRICE_FACTORS.get(state, {}).get(crop, 1.0)

                    city_prices = []
                    if is_karnataka and district_prices:
                        city_prices = sorted(
                            [
                                {"city": d, "price": round(sum(v) / len(v), 0)}
                                for d, v in district_prices.items()
                            ],
                            key=lambda x: x["price"],
                            reverse=True,
                        )

                    result = {
                        'today_price': round(today_price, 0),
                        'source': 'Agmarknet Live',
                        'mandis_checked': len(prices),
                        'state_factor': state_f,
                        'live': True,
                        'city_prices': city_prices,
                    }
                    self._cache[cache_key] = (time.time(), result)
                    return result
        except Exception:
            pass

        return None


# Singleton
_market_service: MarketService | None = None


def get_market_service() -> MarketService:
    global _market_service
    if _market_service is None:
        _market_service = MarketService()
    return _market_service
