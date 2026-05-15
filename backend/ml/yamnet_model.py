"""
YAMNet acoustic pest detector — primary acoustic classifier.

Pipeline at runtime:
    raw PCM → resample to 16 kHz mono → YAMNet → mean-pooled 1024-dim
    embedding → trained classifier head → temperature-scaled softmax →
    crop-prior reweighting → abstain gate → pest JSON.

The classifier head is produced by `scripts/train_yamnet_head.py` and persisted
to `backend/models/yamnet_head.joblib`. The bundle may carry an optional
`temperature` float (fit on the val set during training); when absent it
defaults to 1.0 and the path behaves exactly as before. Same goes for the
'Quiet' and 'Non-biological' negative classes — they are only reachable if
the head was trained with those folders present in `data/audio_samples/`.

If the head file is missing or TF / TF Hub is unavailable, `load()` raises
and the router falls through to the Gemini→Claude API path
(see backend/routers/acoustic.py).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from backend.core.constants import (
    PEST_META,
    CROP_PEST_PRIORS,
    CROP_PEST_PRIOR_DEFAULT,
)

logger = logging.getLogger(__name__)

YAMNET_TFHUB = "https://tfhub.dev/google/yamnet/1"
SAMPLE_RATE = 16000
HEAD_PATH = Path(__file__).resolve().parent.parent / "models" / "yamnet_head.joblib"

# Abstain thresholds — applied AFTER calibration and crop-prior reweighting.
# top1 must clear ABSTAIN_TOP1 in absolute probability AND beat top2 by at
# least ABSTAIN_MARGIN, otherwise we raise YAMNetAbstain and the router
# falls through to the API fallback (or surfaces 'uncertain' when offline).
ABSTAIN_TOP1 = 0.45
ABSTAIN_MARGIN = 0.10

# Sliding-window aggregation. YAMNet emits one 1024-d embedding per ~0.48 s
# frame. We chunk frames into ~3 s windows (with 50 % overlap), classify each
# window's mean-pooled embedding, and aggregate the per-window softmax
# probabilities by median. Median is robust to a single noisy burst (wind
# gust, mic bump) hijacking the call — a problem the original "mean-pool the
# whole clip into one vector" path was vulnerable to.
WINDOW_FRAMES = 6   # ≈ 2.9 s
WINDOW_STRIDE = 3   # ≈ 1.4 s hop (50 % overlap)

_SINGLETON: Optional["YAMNetBundle"] = None


class YAMNetAbstain(Exception):
    """Raised when YAMNet's softmax is too weak/ambiguous to commit to a call.

    The router catches this distinctly from real errors so the logs make it
    obvious whether the local path refused (abstain) or crashed (predict
    failed). Both routes lead to the API fallback in the same way.
    """


def _resample_to_16k(pcm: np.ndarray, src_rate: int) -> np.ndarray:
    """Resample PCM to 16 kHz mono float32 in [-1, 1]."""
    if pcm.ndim > 1:
        pcm = pcm[:, 0]
    pcm = pcm.astype(np.float32, copy=False)
    if src_rate == SAMPLE_RATE:
        return pcm
    from math import gcd
    from scipy.signal import resample_poly
    g = gcd(int(src_rate), SAMPLE_RATE)
    up = SAMPLE_RATE // g
    down = int(src_rate) // g
    resampled = resample_poly(pcm, up, down)
    return resampled.astype(np.float32, copy=False)


def _probs_from_clf(clf, feat: np.ndarray, temperature: float) -> np.ndarray:
    """Compute calibrated class probabilities from the trained head.

    Prefers `decision_function` (true logits) when available, falling back
    to log(predict_proba) for classifiers without logits exposed (MLP).
    Temperature is applied multiplicatively on the logit scale and the
    result is re-softmaxed — T=1.0 is a pass-through.
    """
    T = max(float(temperature), 1e-3)
    if hasattr(clf, "decision_function"):
        scores = np.atleast_2d(clf.decision_function(feat))[0]
        if scores.ndim == 0:
            scores = np.array([scores])
        # Binary LogReg returns a single scalar; expand to [-s, s].
        if scores.size == 1:
            scores = np.array([-scores[0], scores[0]])
    elif hasattr(clf, "predict_proba"):
        proba = clf.predict_proba(feat)[0]
        scores = np.log(np.clip(proba, 1e-9, 1.0))
    else:
        # Last resort — unreachable for the heads we train here.
        return np.array([1.0])

    scaled = scores / T
    scaled = scaled - scaled.max()
    probs = np.exp(scaled)
    s = probs.sum()
    return probs / s if s > 0 else probs


def _apply_crop_prior(probs: np.ndarray, classes: list[str],
                      crop_type: str) -> tuple[np.ndarray, bool]:
    """Reweight softmax by per-crop ecological priors and renormalize.

    Returns (new_probs, applied_flag). `applied_flag` is False when the
    crop has no prior table — useful for the diagnostic surface in the UI.
    """
    crop_key = (crop_type or "").strip().title()
    prior_map = CROP_PEST_PRIORS.get(crop_key)
    if not prior_map:
        return probs, False

    weights = np.array(
        [float(prior_map.get(c, CROP_PEST_PRIOR_DEFAULT)) for c in classes],
        dtype=np.float32,
    )
    weighted = probs * weights
    s = float(weighted.sum())
    if s <= 0:
        return probs, False
    return weighted / s, True


class YAMNetBundle:
    """Loaded YAMNet model + trained classifier head + label encoder."""

    def __init__(self, yamnet, clf, label_encoder, classes: list[str],
                 test_accuracy: Optional[float] = None,
                 trained_at: Optional[str] = None,
                 temperature: float = 1.0):
        self.yamnet = yamnet
        self.clf = clf
        self.le = label_encoder
        self.classes = classes
        self.test_accuracy = test_accuracy
        self.trained_at = trained_at
        self.temperature = float(temperature) if temperature else 1.0

    def predict(self, pcm: np.ndarray, rate: int,
                crop_type: str = "Unknown",
                weather_noise_score: float = 0.0) -> dict:
        """Classify a single PCM clip into one PEST_META class.

        Raises YAMNetAbstain when calibrated top-1 probability is below
        ABSTAIN_TOP1, or when the margin to top-2 is below ABSTAIN_MARGIN.
        """
        wave_16k = _resample_to_16k(pcm, rate)
        if wave_16k.size < SAMPLE_RATE // 2:
            raise ValueError("audio too short for YAMNet (<0.5 s after resample)")

        # YAMNet returns (scores, embeddings, log_mel). embeddings: (frames, 1024)
        _, emb, _ = self.yamnet(wave_16k)
        emb_np = emb.numpy()
        n_frames = emb_np.shape[0]

        # Sliding-window: chunk frames into ≈3 s windows, mean-pool each, run
        # the head, then median-aggregate the resulting softmax vectors. Falls
        # back to a single mean-pool when the clip is too short for even one
        # full window — same behavior as the original path.
        window_probs: list[np.ndarray] = []
        if n_frames >= WINDOW_FRAMES:
            for start in range(0, n_frames - WINDOW_FRAMES + 1, WINDOW_STRIDE):
                chunk = emb_np[start:start + WINDOW_FRAMES].mean(axis=0).reshape(1, -1)
                window_probs.append(_probs_from_clf(self.clf, chunk, self.temperature))

        if window_probs:
            stacked = np.vstack(window_probs)
            probs = np.median(stacked, axis=0)
            probs = probs / probs.sum() if probs.sum() > 0 else probs
            n_windows = len(window_probs)
        else:
            feat = emb_np.mean(axis=0).reshape(1, -1)
            probs = _probs_from_clf(self.clf, feat, self.temperature)
            n_windows = 1

        # Map encoder indices → class names (in encoder order) so the prior
        # vector and the softmax line up.
        ordered_classes = [str(self.le.inverse_transform([i])[0])
                           for i in range(len(probs))]
        probs, prior_applied = _apply_crop_prior(probs, ordered_classes, crop_type)

        # Weather noise gate: when the router's heuristic detects wind/rain,
        # suppress all pest-class probabilities and compensate non-biological
        # classes upward, then renormalize. Threshold 0.4 avoids false muting
        # on mildly noisy clips; weight caps at 0.6 so the gate never fully
        # zeroes a confident detection.
        if weather_noise_score > 0.4:
            weight = weather_noise_score * 0.6
            non_bio_idx = [
                i for i, c in enumerate(ordered_classes)
                if c in ("Quiet", "Non-biological")
            ]
            probs = probs * (1.0 - weight)
            for idx in non_bio_idx:
                probs[idx] *= 1.0 + weight
            s = probs.sum()
            if s > 0:
                probs = probs / s

        order = np.argsort(probs)[::-1]
        top1_idx = int(order[0])
        top2_idx = int(order[1]) if len(order) > 1 else top1_idx
        top1_p = float(probs[top1_idx])
        top2_p = float(probs[top2_idx])
        margin = top1_p - top2_p

        if top1_p < ABSTAIN_TOP1 or margin < ABSTAIN_MARGIN:
            raise YAMNetAbstain(
                f"low_confidence top1={top1_p:.2f} margin={margin:.2f}"
            )

        pred_label = ordered_classes[top1_idx]
        confidence = int(round(top1_p * 100))

        top3 = [
            (ordered_classes[i], int(round(float(probs[i]) * 100)))
            for i in order[:3]
        ]
        all_class_confidence = {
            ordered_classes[i]: int(round(float(probs[i]) * 100))
            for i in order
        }

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
            "all_class_confidence": all_class_confidence,
            "_model_used": "yamnet",
            "_test_accuracy": self.test_accuracy,
            "_temperature": self.temperature,
            "_crop_prior_applied": prior_applied,
            "_n_windows": n_windows,
            "weather_noise_score": round(float(weather_noise_score), 3),
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
        temperature=bundle_dict.get("temperature", 1.0),
    )
    logger.info(
        "YAMNet ready — %d classes, test_accuracy=%.3f, T=%.2f",
        len(_SINGLETON.classes),
        _SINGLETON.test_accuracy or 0.0,
        _SINGLETON.temperature,
    )

    # Vocab alignment with the API-path prompts: every local class should
    # exist in PEST_META, and any PEST_META label the API prompts can emit
    # should be present locally (otherwise the two pipelines disagree on
    # vocabulary and aggregation/UI fields fall back to neutral defaults).
    local = set(_SINGLETON.classes)
    canonical = set(PEST_META.keys())
    missing_in_meta = local - canonical
    missing_in_head = canonical - local
    if missing_in_meta:
        logger.warning(
            "YAMNet head emits labels missing from PEST_META: %s",
            sorted(missing_in_meta),
        )
    if missing_in_head:
        logger.info(
            "PEST_META labels not in current YAMNet head (API path only): %s",
            sorted(missing_in_head),
        )

    return _SINGLETON
