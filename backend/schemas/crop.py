"""Pydantic schemas for crop recommendation endpoint."""

from pydantic import BaseModel, Field


class CropRecommendRequest(BaseModel):
    """Input: soil nutrients + climate conditions."""
    N: float = Field(..., ge=0, le=140, description="Nitrogen (kg/ha)")
    P: float = Field(..., ge=5, le=145, description="Phosphorus (kg/ha)")
    K: float = Field(..., ge=5, le=205, description="Potassium (kg/ha)")
    temperature: float = Field(..., ge=8, le=45, description="Temperature (°C)")
    humidity: float = Field(..., ge=14, le=100, description="Humidity (%)")
    ph: float = Field(..., ge=3.5, le=9.5, description="Soil pH")
    rainfall: float = Field(..., ge=20, le=300, description="Rainfall (mm)")


class SoilInfo(BaseModel):
    soil_type: str
    advice: str
    indicator: str


class CropPrediction(BaseModel):
    crop: str
    confidence: float
    emoji: str


class CropRecommendResponse(BaseModel):
    """Output: top crops + soil analysis."""
    top_crop: CropPrediction
    alternatives: list[CropPrediction]
    tip: str
    soil: SoilInfo
    all_probabilities: dict[str, float]
