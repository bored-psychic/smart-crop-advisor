"""Pydantic schemas for acoustic pest detection endpoint."""

from typing import Optional, Literal
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
    band_energy: Optional[dict] = None
    claude_advice: Optional[str] = None

    analysis_method: Literal[
        "claude_vision",
        "gemini_audio",
        "uncertain",
        "random_forest_offline_demo",
        "rejected",
    ] = "rejected"
    decode_method: Optional[Literal["scipy_wav", "pydub_ffmpeg"]] = None
    truncated: bool = False
    analyzed_seconds: float = 0.0
    duration_seconds: float = 0.0
    sample_rate: int = 0
    quality_warnings: list[str] = Field(default_factory=list)
    cv_accuracy: Optional[float] = None
    cv_label: Optional[str] = None
    methodology_note: Optional[str] = None

    is_pest: Optional[bool] = None
    claude_failure_stage: Optional[str] = None
    claude_failure_detail: Optional[str] = None
    claude_model_used: Optional[str] = None
