from fastapi import APIRouter, HTTPException
from services.market import MarketService
from core.cache import cache_response
from core.config import settings

router = APIRouter()

@router.get("/price/{state}/{crop}")
@cache_response(ttl=settings.CACHE_TTL_MARKET, key_prefix="market_api")
async def get_market_price(state: str, crop: str):
    data = await MarketService.get_live_mandi_price(crop, state)
    if not data:
        # Fallback to forecast calibration logic (simplified for API)
        return {"live": False, "msg": "Live price unavailable, check forecast."}
    return data
