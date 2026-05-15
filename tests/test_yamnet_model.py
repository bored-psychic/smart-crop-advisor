"""Smoke tests for the YAMNet acoustic wrapper.

These tests are skipped when:
  - tensorflow / tensorflow-hub are not installed (lightweight CI environments)
  - the trained classifier head (backend/models/yamnet_head.joblib) is not
    present (training requires data + several minutes; gated separately)

When both prerequisites are met, the tests verify:
  1. YAMNetBundle.predict returns a dict with the contract _coerce_claude_prediction expects
  2. The predicted class is one of the trained classes
  3. _resample_to_16k passes through 16 kHz inputs and resamples others
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HEAD_PATH = REPO_ROOT / "backend" / "models" / "yamnet_head.joblib"


tf_hub = pytest.importorskip("tensorflow_hub")  # noqa: F841 — gate the module
pytestmark = pytest.mark.skipif(
    not HEAD_PATH.exists(),
    reason=(
        "YAMNet classifier head not trained yet. "
        "Run scripts/fetch_audio_dataset.py then scripts/train_yamnet_head.py."
    ),
)


def _synthetic_tone(freq: float = 440.0, duration: float = 2.0,
                    sample_rate: int = 16000) -> np.ndarray:
    """Generate a sine-tone PCM clip — generic audio so the test isn't
    label-sensitive (we only validate the response *shape*, not which class
    YAMNet picks for an arbitrary tone)."""
    t = np.linspace(0, duration, int(duration * sample_rate), endpoint=False)
    return (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_resample_passthrough_at_16k():
    from backend.ml.yamnet_model import _resample_to_16k
    pcm = np.zeros(16000, dtype=np.float32)
    out = _resample_to_16k(pcm, 16000)
    assert out is pcm or np.array_equal(out, pcm)
    assert out.dtype == np.float32


def test_resample_downsamples_44k_to_16k():
    from backend.ml.yamnet_model import _resample_to_16k
    pcm = np.zeros(44100, dtype=np.float32)
    out = _resample_to_16k(pcm, 44100)
    # 44100 -> 16000 is roughly 0.36x length.
    assert 14000 <= out.size <= 18000
    assert out.dtype == np.float32


def test_predict_returns_expected_shape():
    from backend.ml import yamnet_model
    bundle = yamnet_model.load()
    pcm = _synthetic_tone(freq=440.0, duration=2.0, sample_rate=16000)
    result = bundle.predict(pcm, rate=16000, crop_type="Unknown")

    required_keys = {
        "pest", "role", "is_pest", "low_signal", "severity",
        "freq_range", "pattern", "energy_level", "confidence",
        "action", "icon", "top3", "_model_used",
    }
    assert required_keys.issubset(result.keys())
    assert result["_model_used"] == "yamnet"
    assert 0 <= result["confidence"] <= 100
    assert isinstance(result["top3"], list)
    assert result["pest"] in bundle.classes


def test_predict_rejects_too_short_audio():
    from backend.ml import yamnet_model
    bundle = yamnet_model.load()
    pcm = np.zeros(100, dtype=np.float32)  # well under 0.5 s
    with pytest.raises(ValueError):
        bundle.predict(pcm, rate=16000)
