"""Pydantic schemas for field watch (satellite intelligence) endpoint."""

from pydantic import BaseModel, Field


class FieldWatchRequest(BaseModel):
    city: str = Field(..., description="City or nearest town name")


class WeatherInfo(BaseModel):
    temp: float
    feels_like: float
    humidity: int
    wind: float
    description: str
    rain_1h: float
    lat: float
    lon: float


class FloodAlert(BaseModel):
    rain_48h: float
    flood_risk: str  # HIGH, MEDIUM, LOW


class FireAlert(BaseModel):
    hotspots_nearby: int
    risk: str  # HIGH, MEDIUM, NONE, UNKNOWN
    source: str


class LocustAlert(BaseModel):
    swarms_nearby: int
    risk: str  # HIGH, MEDIUM, NONE, UNKNOWN
    source: str


class AQIInfo(BaseModel):
    value: int
    label: str


class FieldWatchResponse(BaseModel):
    city: str
    overall_risk: str  # HIGH, MEDIUM, LOW
    weather: WeatherInfo | None
    flood: FloodAlert | None
    fire: FireAlert | None
    locust: LocustAlert | None
    aqi: AQIInfo | None
