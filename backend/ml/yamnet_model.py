"""
YAMNet acoustic pest detector — primary acoustic classifier.

Pipeline at runtime:
    raw PCM → resample to 16 kHz mono → YAMNet → mean-pooled 1024-dim
    embedding → trained classifier head → pest JSON in the same shape
    `_coerce_claude_prediction` expects.

The classifier head is produced by `scripts/train_yamnet_head.py` and persisted
to `backend/models/yamnet_head.joblib`. If the head file is missing or TF / TF
Hub is unavailable, `load()` raises and the router falls through to the
Gemini→Claude API path (see backend/routers/acoustic.py).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from backend.core.constants import PEST_META

logger = logging.getLogger(__name__)

YAMNET_TFHUB = "https://tfhub.dev/google/yamnet/1"
SAMPLE_RATE = 16000
HEAD_PATH = Path(__file__).resolve().parent.parent / "models" / "yamnet_head.joblib"

_SINGLETON: Optional["YAMNetBundle"] = None


def _resample_to_16k(pcm: np.ndarray, src_rate: int) -> np.ndarray:
    """Resample PCM to 16 kHz mono float32 in [-1, 1]."""
    if pcm.ndim > 1:
        pcm = pcm[:, 0]
    pcm = pcm.astype(np.float32, copy=False)
    if src_rate == SAMPLE_RATE:
        return pcm
    import librosa
    return librosa.resample(pcm, orig_sr=src_rate, target_sr=SAMPLE_RATE)


class YAMNetBundle:
    """Loaded YAMNet model + trained classifier head + label encoder."""

    def __init__(self, yamnet, clf, label_encoder, classes: list[str],
                 test_accuracy: Optional[float] = None,
                 trained_at: Optional[str] = None):
        self.yamnet = yamnet
        self.clf = clf
        self.le = label_encoder
        self.classes = classes
        self.test_accuracy = test_accuracy
        self.trained_at = trained_at

    def predict(self, pcm: np.ndarray, rate: int,
                crop_type: str = "Unknown") -> dict:
        """Classify a single PCM clip into one PEST_META class."""
        wave_16k = _resample_to_16k(pcm, rate)
        if wave_16k.size < SAMPLE_RATE // 2:
            raise ValueError("audio too short for YAMNet (<0.5 s after resample)")

        # YAMNet returns (scores, embeddings, log_mel). embeddings: (frames, 1024)
        _, emb, _ = self.yamnet(wave_16k)
        feat = emb.numpy().mean(axis=0).reshape(1, -1)

        if hasattr(self.clf, "predict_proba"):
            probs = self.clf.predict_proba(feat)[0]
        else:
            # decision_function fallback for classifiers without proba
            scores = self.clf.decision_function(feat)[0]
            probs = np.exp(scores - scores.max())
            probs = probs / probs.sum()

        pred_idx = int(np.argmax(probs))
        pred_label = str(self.le.inverse_transform([pred_idx])[0])
        confidence = int(round(float(probs[pred_idx]) * 100))

        # Top-3 (class names canonical to PEST_META)
        order = np.argsort(probs)[::-1][:3]
        top3 = [
            (str(self.le.inverse_transform([i])[0]),
             int(round(float(probs[i]) * 100)))
            for i in order
        ]

        meta = PEST_META.get(pred_label, {})
        if not meta:
            # Trained class missing from PEST_META — defensive fallback.
            logger.warning("YAMNet predicted unknown class %r; using neutral defaults", pred_label)
            meta = {
                "role": "pest", "severity": "medium", "low_signal": False,
                "freq_range": "—", "pattern": "—", "energy_level": "—",
                "icon": "🐛",
                "action": "Verify visually before treating.",
            }

        return {
            "pest": pred_label,
            "role": meta.get("role", "pest"),
            "is_pest": meta.get("role", "pest") == "pest",
            "low_signal": bool(meta.get("low_signal", False)),
            "severity": meta.get("severity", "medium"),
            "freq_range": meta.get("freq_range", "—"),
            "pattern": meta.get("pattern", "—"),
            "energy_level": meta.get("energy_level", "—"),
            "confidence": max(0, min(100, confidence)),
            "action": meta.get("action", "—"),
            "icon": meta.get("icon", "🐛"),
            "top3": top3,
            "_model_used": "yamnet",
            "_test_accuracy": self.test_accuracy,
        }


def load() -> YAMNetBundle:
    """Load and cache the YAMNet bundle. Raises on TF / Hub / head failure."""
    global _SINGLETON
    if _SINGLETON is not None:
        return _SINGLETON

    if not HEAD_PATH.exists():
        raise FileNotFoundError(
            f"Trained YAMNet head not found at {HEAD_PATH}. "
            "Run scripts/fetch_audio_dataset.py then scripts/train_yamnet_head.py."
        )

    # Lazy imports — TF is heavy and we only want to pay the cost when the
    # model is actually used. Import errors propagate so main.py can route
    # to the API-only fallback.
    import joblib
    import tensorflow_hub as hub  # noqa: F401  (validates TF install)

    logger.info("Loading YAMNet from TF Hub: %s", YAMNET_TFHUB)
    yamnet = hub.load(YAMNET_TFHUB)

    logger.info("Loading classifier head: %s", HEAD_PATH)
    bundle_dict = joblib.load(HEAD_PATH)

    _SINGLETON = YAMNetBundle(
        yamnet=yamnet,
        clf=bundle_dict["clf"],
        label_encoder=bundle_dict["label_encoder"],
        classes=bundle_dict["classes"],
        test_accuracy=bundle_dict.get("test_accuracy"),
        trained_at=bundle_dict.get("trained_at"),
    )
    logger.info(
        "YAMNet ready — %d classes, test_accuracy=%.3f",
        len(_SINGLETON.classes),
        _SINGLETON.test_accuracy or 0.0,
    )
    return _SINGLETON
