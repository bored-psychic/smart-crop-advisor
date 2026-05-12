"""Pydantic schemas for market price + forecast endpoint."""

from pydantic import BaseModel, Field


class MarketForecastRequest(BaseModel):
    crop: str = Field(..., description="Crop name")
    city: str = Field(..., description="City or district name (state is derived via geocoding)")
    forecast_days: int = Field(30, ge=7, le=60, description="Forecast horizon in days")


class CityPrice(BaseModel):
    city: str
    price: float


class LivePrice(BaseModel):
    today_price: float
    source: str
    mandis_checked: int
    state_factor: float
    live: bool
    city_prices: list[CityPrice] = []


class ForecastDay(BaseModel):
    date: str
    price: float
    min_price: float
    max_price: float


class MarketForecastResponse(BaseModel):
    crop: str
    state: str
    city: str
    live_price: LivePrice | None
    forecast: list[ForecastDay]
    best_price: float
    best_date: str
    worst_price: float
    worst_date: str
    avg_price: float
    state_factor: float
    sell_advice: str
