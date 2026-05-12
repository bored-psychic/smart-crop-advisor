"""
Acoustic model loader — thin compatibility shim.

The old synthetic Random Forest has been replaced by YAMNet (see
backend/ml/yamnet_model.py). This module now does two things:

1. Re-exports `_features_from_pcm` (still used by the router for the DSP
   feature panel passed to the Gemini→Claude fallback) and
   `_normalize_crop_type` (still used by the router for the crop dropdown).
2. Provides `load()` that returns the YAMNet bundle, tolerating TF import
   failures by re-raising — `backend/main.py` catches and sets
   `app.state.acoustic_model = None`, which cleanly drops the pipeline to
   the API-only fallback.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


def _normalize_crop_type(crop_type: str) -> str:
    """Normalize user-provided crop labels for downstream display."""
    if not crop_type:
        return "Unknown"

    cleaned = " ".join(str(crop_type).strip().split())
    if not cleaned:
        return "Unknown"

    alias_map = {
        "corn": "Maize",
        "paddy": "Rice",
        "chana": "Chickpea",
    }
    lower = cleaned.lower()
    if lower in alias_map:
        return alias_map[lower]
    return cleaned.title()


def _features_from_pcm(raw: np.ndarray, rate: int) -> list[float] | None:
    """Compute 8 spectral features from already-decoded mono PCM.

    Used by the router to build the DSP feature block handed to the
    Gemini→Claude fallback. Order:
        [low, mid, high, ultra, centroid_Hz, ZCR, peak_bin, energy_variance].
    """
    if raw is None or len(raw) < int(rate * 0.5):
        return None

    seg = raw[:min(len(raw), int(rate * 4))]

    fft_vals = np.abs(np.fft.rfft(seg))
    freqs = np.fft.rfftfreq(len(seg), 1.0 / rate)
    eps = 1e-9

    def band(lo, hi):
        mask = (freqs >= lo) & (freqs < hi)
        return float(np.mean(fft_vals[mask])) if mask.any() else 0.0

    low = band(50, 200)
    mid = band(200, 500)
    high = band(500, 1200)
    ultra = band(1200, 4000)

    centroid = float(np.sum(freqs * fft_vals) / (np.sum(fft_vals) + eps))
    zcr = float(np.mean(np.abs(np.diff(np.sign(seg)))) / 2)
    peak_bin = float(min(int(np.argmax(fft_vals) * 15 / (len(fft_vals) + 1)), 15))

    frame_size = 512
    frames = [seg[i:i + frame_size] for i in range(0, len(seg) - frame_size, frame_size)]
    energies = [float(np.mean(f ** 2)) for f in frames] if frames else [0.0]
    variance = float(np.var(energies))

    return [low, mid, high, ultra, centroid, zcr, peak_bin, variance]


def load():
    """Load the YAMNet bundle. Re-raises on TF/model failure so callers can
    fall through to the API-only path."""
    from backend.ml import yamnet_model
    return yamnet_model.load()
