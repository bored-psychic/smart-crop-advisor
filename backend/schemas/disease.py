"""Pydantic schemas for disease detection endpoints."""

from typing import Optional
from pydantic import BaseModel, Field
from backend.schemas.dosage import DosageAdvice


class DiseaseResult(BaseModel):
    disease: str
    severity: str
    confidence: int
    treatment: str
    prevention: str
    action: str
    model_used: str
    top3: list[tuple[str, int]] = []
    color: Optional[str] = None
    dosage_advice: Optional[DosageAdvice] = None


class SymptomRequest(BaseModel):
    crop: str = Field(..., description="Crop name from DISEASE_DB")
    symptom: str = Field(..., description="Observed symptom text")


class SymptomResponse(BaseModel):
    disease: str
    severity: str
    disease_type: str
    treatment: str
    prevention: str
    crop: str
    symptom: str
    dosage_advice: Optional[DosageAdvice] = None
