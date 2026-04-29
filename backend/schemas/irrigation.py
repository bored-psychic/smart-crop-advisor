"""Pydantic schemas for irrigation advisor endpoint."""

from pydantic import BaseModel, Field


class IrrigationRequest(BaseModel):
    crop: str = Field(..., description="Crop name matching CROP_KC keys")
    growth_stage: str = Field(..., description="Initial, Development, Mid-season, or Late season")
    field_area: float = Field(1.0, ge=0.5, le=100, description="Field area in acres")
    last_rain_mm: float = Field(0, ge=0, le=100, description="Rainfall in last 3 days (mm)")
    temperature: float = Field(30.0, ge=10, le=48, description="Temperature (°C)")
    humidity: float = Field(60.0, ge=10, le=100, description="Humidity (%)")
    wind_speed: float = Field(10.0, ge=0, le=50, description="Wind speed (km/h)")


class FertilizerAdvice(BaseModel):
    nitrogen: str
    tip: str
    growth_stage: str


class IrrigationResponse(BaseModel):
    crop: str
    ET0: float
    Kc: float
    ETc: float
    net_irrigation_mm: float
    total_litres: float
    total_kl: float
    field_area: float
    urgency: str  # "none", "light", "urgent"
    advice: str
    fertilizer: FertilizerAdvice
