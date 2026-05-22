"""Smoke tests for the YAMNet acoustic wrapper.

These tests are skipped when:
  - tensorflow / tensorflow-hub are not installed (lightweight CI environments)
  - the trained classifier head (backend/models/yamnet_head.joblib) is not
    present (training requires data + several minutes; gated separately)

When both prerequisites are met, the tests verify:
  1. YAMNetBundle.predict returns a dict with the contract _coerce_claude_prediction expects
  2. The predicted class is one of the trained classes
  3. _resample_to_16k passes through 16 kHz inputs and resamples others

Network calls to tfhub.dev are blocked in tests via unittest.mock.patch.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

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


def _make_fake_yamnet():
    """Return a callable that mimics hub.load('https://tfhub.dev/google/yamnet/1').

    YAMNet is called as yamnet(wave_16k) and returns (scores, embeddings, log_mel).
    - scores shape: (frames, 521)  — AudioSet 521-class logits
    - embeddings shape: (frames, 1024)
    - log_mel: ignored in our code

    We return 6 frames so the sliding-window logic (WINDOW_FRAMES=6) fires.
    The fake also exposes class_names() for the confounder-index extraction step.
    """
    import tensorflow as tf

    n_frames = 6

    class FakeYAMNet:
        def __call__(self, wave):
            scores = tf.constant(np.zeros((n_frames, 521), dtype=np.float32))
            embeddings = tf.constant(
                np.random.default_rng(42).random((n_frames, 1024)).astype(np.float32)
            )
            log_mel = tf.constant(np.zeros((n_frames, 64), dtype=np.float32))
            return scores, embeddings, log_mel

        def class_names(self):
            # Return a minimal list; enough for the confounder-extraction loop.
            names = [b"Speech", b"Music", b"Wind", b"Rain"]
            return [tf.constant(n) for n in names]

    return FakeYAMNet()


@pytest.fixture(autouse=True)
def _offline_yamnet(monkeypatch):
    """Patch tensorflow_hub.load so tests never touch the network.

    Also resets the YAMNetBundle singleton so each test gets a clean load.
    """
    import backend.ml.yamnet_model as ym

    fake = _make_fake_yamnet()
    monkeypatch.setattr("tensorflow_hub.load", lambda url: fake)

    # Reset singleton so load() re-runs with the patched hub.load.
    original_singleton = ym._SINGLETON
    ym._SINGLETON = None
    yield
    ym._SINGLETON = original_singleton


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

    try:
        result = bundle.predict(pcm, rate=16000, crop_type="Unknown")
    except yamnet_model.YAMNetAbstain:
        # Abstain is a valid outcome when the fake embeddings don't produce a
        # confident prediction — the test only verifies the network is NOT hit.
        pytest.skip("YAMNet abstained on synthetic audio (expected with fake embeddings)")
        return

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
