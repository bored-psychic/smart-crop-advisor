"""
PANNs CNN14 acoustic pest detector — primary acoustic classifier (replaces YAMNet).

Pipeline at runtime:
    raw PCM → resample to 32 kHz mono → CNN14 → 2048-dim embedding +
    527-class AudioSet clipwise softmax → trained classifier head →
    temperature-scaled softmax → crop-prior reweighting →
    weather-noise gate → abstain gate → pest JSON.

The classifier head is produced by `scripts/train_panns_head.py` and persisted
to `backend/models/panns_head.joblib`. The bundle carries an optional
`temperature` float (fit on the val set during training); when absent it
defaults to 1.0.

If the head file is missing, the CNN14 checkpoint is missing, or torch /
panns_inference are unavailable, `load()` raises and the router falls
through to the Gemini→Claude API path.
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

SAMPLE_RATE = 32000  # CNN14's required input rate
HEAD_PATH = Path(__file__).resolve().parent.parent / "models" / "panns_head.joblib"

# Windowed aggregation parameters — MUST match scripts/train_panns_head.py
# (WINDOW_SECONDS / HOP_SECONDS). The training script writes its values into
# the bundle; load() asserts they line up so a train/inference drift fails
# loudly instead of silently mispredicting.
WINDOW_SECONDS = 2.0
HOP_SECONDS = 1.0

# Same calibration bar as the YAMNet path — top1 must clear ABSTAIN_TOP1
# AND beat top2 by ABSTAIN_MARGIN, otherwise we abstain and the router
# falls through to the API fallback (or surfaces 'uncertain' when offline).
ABSTAIN_TOP1 = 0.45
ABSTAIN_MARGIN = 0.10

_SINGLETON: Optional["PANNsBundle"] = None


class PANNsAbstain(Exception):
    """Raised when CNN14's calibrated softmax is too weak/ambiguous to commit."""


class SoftVoteEnsemble:
    """Soft-voting ensemble: average predict_proba across constituent fitted
    models. Used by scripts/train_panns_head.py Tier-3 head selection when the
    ensemble beats every single classifier on val. Defined here so joblib can
    unpickle the bundle from the backend without importing scripts/."""

    def __init__(self, models: list, name: str = "ensemble"):
        self.models = models
        self.name = name
        self.classes_ = models[0].classes_

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return np.mean([m.predict_proba(X) for m in self.models], axis=0)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.classes_[np.argmax(self.predict_proba(X), axis=1)]


def _resample_to_32k(pcm: np.ndarray, src_rate: int) -> np.ndarray:
    """Resample PCM to 32 kHz mono float32 in [-1, 1]."""
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
    """Temperature-scaled probabilities from the trained head.

    Prefers `decision_function` logits; falls back to log(predict_proba).
    Identical math to the YAMNet path — keeps abstain thresholds comparable.
    """
    T = max(float(temperature), 1e-3)
    if hasattr(clf, "decision_function"):
        scores = np.atleast_2d(clf.decision_function(feat))[0]
        if scores.ndim == 0:
            scores = np.array([scores])
        if scores.size == 1:
            scores = np.array([-scores[0], scores[0]])
    elif hasattr(clf, "predict_proba"):
        proba = clf.predict_proba(feat)[0]
        scores = np.log(np.clip(proba, 1e-9, 1.0))
    else:
        return np.array([1.0])

    scaled = scores / T
    scaled = scaled - scaled.max()
    probs = np.exp(scaled)
    s = probs.sum()
    return probs / s if s > 0 else probs


def _apply_crop_prior(probs: np.ndarray, classes: list[str],
                      crop_type: str) -> tuple[np.ndarray, bool]:
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


class PANNsBundle:
    """Loaded CNN14 model + trained classifier head + label encoder."""

    def __init__(self, audio_tagger, clf, label_encoder, classes: list[str],
                 test_accuracy: Optional[float] = None,
                 trained_at: Optional[str] = None,
                 temperature: float = 1.0,
                 confounder_indices: Optional[list[int]] = None):
        self.audio_tagger = audio_tagger
        self.clf = clf
        self.le = label_encoder
        self.classes = classes
        self.test_accuracy = test_accuracy
        self.trained_at = trained_at
        self.temperature = float(temperature) if temperature else 1.0
        self.confounder_indices: list[int] = confounder_indices or []

    def _embed(self, wave_32k: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return (mean_clipwise_527, mean_embedding_2048) for one clip.

        Chunks the waveform into WINDOW_SECONDS / HOP_SECONDS windows, runs
        CNN14 over the batch, and mean-pools the per-window outputs. Mirrors
        scripts/train_panns_head.py:embed_clip_windowed so train and inference
        see the same feature distribution.
        """
        win = int(WINDOW_SECONDS * SAMPLE_RATE)
        hop = int(HOP_SECONDS * SAMPLE_RATE)
        pcm = wave_32k.astype(np.float32, copy=False)
        if pcm.size < win:
            repeats = (win + pcm.size - 1) // pcm.size
            pcm = np.tile(pcm, repeats)[:win]
            audio = pcm.reshape(1, win)
        else:
            n = 1 + (pcm.size - win) // hop
            audio = np.stack([pcm[i * hop:i * hop + win] for i in range(n)])
        clipwise, embedding = self.audio_tagger.inference(audio)
        return clipwise.mean(axis=0), embedding.mean(axis=0)

    def predict(self, pcm: np.ndarray, rate: int,
                crop_type: str = "Unknown",
                weather_noise_score: float = 0.0) -> dict:
        """Classify a single PCM clip into one PEST_META class.

        Raises PANNsAbstain when calibrated top-1 < ABSTAIN_TOP1 or the
        margin to top-2 < ABSTAIN_MARGIN.
        """
        wave_32k = _resample_to_32k(pcm, rate)
        if wave_32k.size < SAMPLE_RATE // 2:
            raise ValueError("audio too short for CNN14 (<0.5 s after resample)")

        clipwise, embedding = self._embed(wave_32k)

        # AudioSet confounder mass — same trick as YAMNet, just sourced from
        # CNN14's 527-class output instead of YAMNet's 521-class output.
        cnn_noise_score = 0.0
        if self.confounder_indices:
            cnn_noise_score = float(
                np.clip(clipwise[self.confounder_indices].sum(), 0.0, 1.0)
            )
        blended_noise = float(np.clip(
            max(weather_noise_score, cnn_noise_score), 0.0, 1.0
        ))

        # Head input is the 2048-d embedding concatenated with the 527-d
        # AudioSet clipwise softmax — matches scripts/train_panns_head.py.
        feat = np.concatenate([embedding, clipwise], axis=0).reshape(1, -1)
        probs = _probs_from_clf(self.clf, feat, self.temperature)

        ordered_classes = [str(self.le.inverse_transform([i])[0])
                           for i in range(len(probs))]
        probs, prior_applied = _apply_crop_prior(probs, ordered_classes, crop_type)

        # Weather noise gate: when wind/rain noise dominates, suppress pest
        # probabilities and lift Non-biological/Quiet, then renormalize.
        if blended_noise > 0.4:
            weight = blended_noise * 0.6
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
            raise PANNsAbstain(
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
            logger.warning("CNN14 predicted unknown class %r; using neutral defaults", pred_label)
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
            "_model_used": "panns",
            "_test_accuracy": self.test_accuracy,
            "_temperature": self.temperature,
            "_crop_prior_applied": prior_applied,
            "_n_windows": 1,
            "weather_noise_score": round(blended_noise, 3),
            "yamnet_noise_score": round(cnn_noise_score, 3),
        }


def load() -> PANNsBundle:
    """Load and cache the PANNs bundle. Raises on torch/checkpoint/head failure."""
    global _SINGLETON
    if _SINGLETON is not None:
        return _SINGLETON

    if not HEAD_PATH.exists():
        raise FileNotFoundError(
            f"Trained PANNs head not found at {HEAD_PATH}. "
            "Run scripts/fetch_audio_dataset.py then scripts/train_panns_head.py."
        )

    import joblib
    # Lazy import — torch + panns_inference are heavy and only needed when the
    # local model actually runs.
    from panns_inference import AudioTagging
    from panns_inference.config import labels as audioset_labels

    logger.info("Loading CNN14 via panns_inference …")
    audio_tagger = AudioTagging(checkpoint_path=None, device="cpu")

    _CONFOUNDER_SUBSTRINGS = (
        "wind", "rain", "rustling", "white noise", "pink noise",
        "static", "engine", "motor vehicle", "pump",
    )
    try:
        confounder_indices = [
            i for i, n in enumerate(audioset_labels)
            if any(s in n.lower() for s in _CONFOUNDER_SUBSTRINGS)
        ]
        logger.info(
            "CNN14 confounder indices (%d classes): %s",
            len(confounder_indices), confounder_indices,
        )
    except Exception as exc:
        logger.warning("Could not extract AudioSet class names for confounder gate: %s", exc)
        confounder_indices = []

    logger.info("Loading classifier head: %s", HEAD_PATH)
    bundle_dict = joblib.load(HEAD_PATH)

    # Sanity-check: the runtime concat is 2048 (embedding) + 527 (clipwise) =
    # 2575. If the saved bundle was trained on a different feature dim
    # (e.g. legacy 2048-only), refuse to load — load() raises and the router
    # falls through to the API path rather than mis-predicting silently.
    expected_dim = 2048 + 527
    saved_dim = bundle_dict.get("feature_dim")
    if saved_dim is not None and int(saved_dim) != expected_dim:
        raise RuntimeError(
            f"PANNs head feature_dim={saved_dim} does not match runtime "
            f"({expected_dim}). Re-run scripts/train_panns_head.py to "
            "regenerate the bundle with the current feature pipeline."
        )

    _SINGLETON = PANNsBundle(
        audio_tagger=audio_tagger,
        clf=bundle_dict["clf"],
        label_encoder=bundle_dict["label_encoder"],
        classes=bundle_dict["classes"],
        test_accuracy=bundle_dict.get("test_accuracy"),
        trained_at=bundle_dict.get("trained_at"),
        temperature=bundle_dict.get("temperature", 1.0),
        confounder_indices=confounder_indices,
    )
    logger.info(
        "PANNs ready — %d classes, test_accuracy=%.3f, T=%.2f, feature_dim=%d",
        len(_SINGLETON.classes),
        _SINGLETON.test_accuracy or 0.0,
        _SINGLETON.temperature,
        expected_dim,
    )

    local = set(_SINGLETON.classes)
    canonical = set(PEST_META.keys())
    missing_in_meta = local - canonical
    missing_in_head = canonical - local
    if missing_in_meta:
        logger.warning(
            "PANNs head emits labels missing from PEST_META: %s",
            sorted(missing_in_meta),
        )
    if missing_in_head:
        logger.info(
            "PEST_META labels not in current PANNs head (API path only): %s",
            sorted(missing_in_head),
        )

    return _SINGLETON
