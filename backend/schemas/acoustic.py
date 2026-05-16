"""Pydantic schemas for acoustic pest detection endpoint."""

from typing import Optional, Literal
from pydantic import BaseModel, Field
from backend.schemas.dosage import DosageAdvice


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
        "panns",
        "yamnet",
        "claude_vision",
        "gemini_audio",
        "uncertain",
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

    # Local-model diagnostics — populated when analysis_method ∈ {'panns', 'yamnet'}.
    # all_class_confidence: full softmax (post-calibration, post-crop-prior)
    # surfaced for transparency. crop_prior_applied / calibration_temperature
    # let the UI explain *why* the call is what it is.
    all_class_confidence: Optional[dict] = None
    crop_prior_applied: Optional[bool] = None
    calibration_temperature: Optional[float] = None

    # Weather noise diagnostics — 0.0 (clean) to 1.0 (heavy wind/rain).
    # weather_noise_score: blended max(DSP heuristic, AudioSet confounder mass).
    # yamnet_noise_score: raw confounder-class probability mass (named for
    # backwards-compat; under PANNs it sources from CNN14's 527-class output).
    # Both populated only when the local model ran; None on API-fallback paths.
    weather_noise_score: Optional[float] = None
    yamnet_noise_score: Optional[float] = None

    # Audible-insect taxonomy metadata. role drives how the frontend renders
    # results (pest=treatment, pollinator=protect, vector=health-advisory,
    # ambient=indicator only). low_signal=True flags Tier 2 entries where
    # the user should verify visually before treating.
    role: Literal["pest", "pollinator", "vector", "ambient"] = "pest"
    low_signal: bool = False

    # Active-learning feedback hook. Populated when confidence is low enough
    # that farmer correction would be valuable. Frontend uses this to show the
    # "Help improve the AI" widget; submitting feedback moves the clip to the
    # training queue.
    clip_id: Optional[str] = None

    # Dosage recommendation — populated when role == "pest" and pest is identified.
    dosage_advice: Optional[DosageAdvice] = None
