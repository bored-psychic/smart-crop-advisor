"""Pydantic schemas for soil analysis endpoint."""

from pydantic import BaseModel, Field
from typing import Optional


class NutrientDeficiency(BaseModel):
    """Single nutrient or pH deficiency."""
    nutrient: str = Field(..., description="Nutrient name (N, P, K, pH, organic_matter)")
    current_value: float = Field(..., description="Current measured value")
    optimal_min: float = Field(..., description="Optimal minimum")
    optimal_max: float = Field(..., description="Optimal maximum")
    deficit: float = Field(..., description="Shortfall below optimal minimum")
    severity: str = Field(..., description="high|medium|low")


class Amendment(BaseModel):
    """Single amendment recommendation."""
    name: str = Field(..., description="Amendment name (e.g., 'Urea', 'Agricultural Lime')")
    deficiency_target: str = Field(..., description="Which deficiency(ies) this addresses")
    dose_kg_per_acre: Optional[float] = Field(None, description="Dose in kg/acre")
    dose_kg_per_hectare: Optional[float] = Field(None, description="Dose in kg/hectare")
    dose_tonnes_per_acre: Optional[float] = Field(None, description="Dose in tonnes/acre")
    dose_tonnes_per_hectare: Optional[float] = Field(None, description="Dose in tonnes/hectare")
    time_to_effect_days: int = Field(..., description="Days to see effect")
    application_method: str = Field(..., description="How to apply")
    notes: str = Field(..., description="Additional guidance")


class SoilAnalysisRequest(BaseModel):
    """Input: soil test results."""
    N: float = Field(..., ge=0, le=140, description="Nitrogen (kg/ha)")
    P: float = Field(..., ge=5, le=145, description="Phosphorus (kg/ha)")
    K: float = Field(..., ge=5, le=205, description="Potassium (kg/ha)")
    ph: float = Field(..., ge=3.5, le=9.5, description="Soil pH")
    organic_matter_pct: float = Field(..., ge=0, le=20, description="Organic matter (%)")
    target_crop: Optional[str] = Field(None, description="Crop to recommend amendments for")
    area_acres: Optional[float] = Field(None, ge=0, description="Area in acres (for dose calculation)")


class SoilAnalysisResponse(BaseModel):
    """Output: deficiencies + amendments + narrative."""
    deficiencies: list[NutrientDeficiency] = Field(..., description="List of detected deficiencies")
    amendments: list[Amendment] = Field(..., description="Recommended amendments")
    soil_type: str = Field(..., description="Classified soil type")
    narrative: str = Field(..., description="Farmer-readable advisory paragraph")
    compatible_crops: list[str] = Field(..., description="Crops suited to this soil profile")
