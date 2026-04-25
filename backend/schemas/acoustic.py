"""Pydantic schemas for acoustic pest detection endpoint."""

from pydantic import BaseModel, Field


class AcousticResponse(BaseModel):
    pest: str
    severity: str
    confidence: int
    freq_range: str
    pattern: str
    energy_level: str
    action: str
    icon: str
    top3: list[tuple[str, int]] = []
    ml_used: bool
