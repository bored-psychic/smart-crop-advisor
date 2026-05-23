"""Market price + forecast router."""

from fastapi import APIRouter, Request, Depends
from backend.schemas.errors import http_error
from backend.schemas.market import MarketForecastRequest, MarketForecastResponse, LivePrice, ForecastDay, CityPrice
from backend.services.market_service import get_market_service
from backend.services.weather_service import resolve_city_state
from backend.ml import price_model
from backend.data.state_prices import STATE_PRICE_FACTORS
from backend.auth import require_user_or_api_key

router = APIRouter(prefix="/api/market", tags=["Market Prices"])


@router.post("/forecast", response_model=MarketForecastResponse)
async def get_forecast(
    req: MarketForecastRequest,
    request: Request,
    _=Depends(require_user_or_api_key),
):
    """Get live mandi price + Prophet forecast. State is derived from city via geocoding."""
    state = await resolve_city_state(req.city)
    if not state:
        raise http_error(
            422,
            "city_not_resolved",
            f"Could not determine state for city '{req.city}'. Please check the city name.",
        )

    market_svc = get_market_service()

    # Live Agmarknet price
    live_data = await market_svc.get_live_price(req.crop, state)

    live_price = None
    if live_data:
        city_prices = [CityPrice(**cp) for cp in live_data.get('city_prices', [])]
        live_price = LivePrice(
            today_price=live_data['today_price'],
            source=live_data['source'],
            mandis_checked=live_data['mandis_checked'],
            state_factor=live_data['state_factor'],
            live=live_data['live'],
            city_prices=city_prices,
        )

    # Prophet forecast
    price_models = request.app.state.price_models
    forecast_result = price_model.forecast(
        price_models, req.crop, state, req.forecast_days
    )

    if forecast_result is None:
        state_factor = STATE_PRICE_FACTORS.get(state, {}).get(req.crop, 1.0)
        return MarketForecastResponse(
            crop=req.crop,
            state=state,
            city=req.city,
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
        state=state,
        city=req.city,
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
