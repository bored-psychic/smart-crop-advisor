"""Market price + forecast router."""

from fastapi import APIRouter, Request, Depends
from backend.schemas.market import MarketForecastRequest, MarketForecastResponse, LivePrice, ForecastDay
from backend.services.market_service import get_market_service
from backend.ml import price_model
from backend.data.state_prices import STATE_PRICE_FACTORS
from backend.auth import require_api_key

router = APIRouter(prefix="/api/market", tags=["Market Prices"])


@router.post("/forecast", response_model=MarketForecastResponse)
async def get_forecast(
    req: MarketForecastRequest,
    request: Request,
    _: str = Depends(require_api_key),
):
    """Get live mandi price + Prophet forecast with state calibration."""
    market_svc = get_market_service()

    # Live Agmarknet price
    live_data = await market_svc.get_live_price(req.crop, req.state)
    live_price = LivePrice(**live_data) if live_data else None

    # Prophet forecast
    price_models = request.app.state.price_models
    forecast_result = price_model.forecast(
        price_models, req.crop, req.state, req.forecast_days
    )

    if forecast_result is None:
        state_factor = STATE_PRICE_FACTORS.get(req.state, {}).get(req.crop, 1.0)
        return MarketForecastResponse(
            crop=req.crop,
            state=req.state,
            live_price=live_price,
            forecast=[],
            best_price=live_data['today_price'] if live_data else 0,
            best_date="N/A",
            worst_price=live_data['today_price'] if live_data else 0,
            worst_date="N/A",
            avg_price=live_data['today_price'] if live_data else 0,
            state_factor=state_factor,
            sell_advice="Prophet model not available for this crop.",
        )

    return MarketForecastResponse(
        crop=req.crop,
        state=req.state,
        live_price=live_price,
        forecast=[ForecastDay(**f) for f in forecast_result['forecast']],
        best_price=forecast_result['best_price'],
        best_date=forecast_result['best_date'],
        worst_price=forecast_result['worst_price'],
        worst_date=forecast_result['worst_date'],
        avg_price=forecast_result['avg_price'],
        state_factor=forecast_result['state_factor'],
        sell_advice=forecast_result['sell_advice'],
    )
