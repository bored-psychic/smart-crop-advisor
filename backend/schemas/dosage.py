"""Pydantic schemas for dosage recommendation endpoint."""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class DosageRequest(BaseModel):
    pest_id: str
    crop: str
    crop_stage_days: int = Field(0, ge=0)
    area_acres: float = Field(1.0, gt=0)
    state: Optional[str] = None


class DosageAdvice(BaseModel):
    chemical_name: str
    formulation: str
    total_quantity_ml: float
    water_litres: float
    timing: str
    reapply_after_days: int
    total_cost_inr: float
    roi_protected_inr: Optional[float]  # None if mandi price unavailable
    narrative: str                       # Haiku-generated (Task 3) — placeholder for now
    source: Literal["db", "llm_fallback"]
