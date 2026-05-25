"""Unit tests for backend/ml/orthoptera_cicada_gate.py."""
from __future__ import annotations

import numpy as np
import pytest

from backend.ml.orthoptera_cicada_gate import (
    apply_gate,
    discriminator_score,
    GATE_MARGIN_FLOOR,
    GATE_NUDGE_CAP,
    ORTHOPTERA_LABELS,
    CICADA_LABEL,
)


CLASSES = ["Bee", "Beetle", "Cicada", "Cricket", "Grasshopper", "Locust",
           "Non-biological", "Wasp"]


def _probs(d: dict) -> np.ndarray:
    arr = np.zeros(len(CLASSES), dtype=np.float32)
    for k, v in d.items():
        arr[CLASSES.index(k)] = v
    arr = arr / arr.sum()
    return arr


def _per_window_probs(class_to_pattern: dict, n_windows: int = 5) -> np.ndarray:
    """Build a (n_windows, n_classes) matrix from per-class per-window arrays."""
    out = np.zeros((n_windows, len(CLASSES)), dtype=np.float32)
    for cls, pattern in class_to_pattern.items():
        out[:, CLASSES.index(cls)] = pattern
    out = out / out.sum(axis=1, keepdims=True)
    return out


# --- discriminator_score ------------------------------------------------

def test_discriminator_low_variance_cicada_favors_cicada():
    pwp = _per_window_probs({
        "Cicada":      np.array([0.5, 0.5, 0.5, 0.5, 0.5]),
        "Grasshopper": np.array([0.1, 0.4, 0.1, 0.4, 0.1]),
    })
    s = discriminator_score(pwp, CLASSES, onset_density_per_sec=1.0)
    assert s > 0, f"expected score > 0 (favor cicada), got {s}"


def test_discriminator_high_onset_density_favors_ortho():
    pwp = _per_window_probs({
        "Cicada":      np.array([0.3, 0.3, 0.3, 0.3, 0.3]),
        "Grasshopper": np.array([0.3, 0.3, 0.3, 0.3, 0.3]),
    })
    s = discriminator_score(pwp, CLASSES, onset_density_per_sec=8.0)
    assert s < 0, f"expected score < 0 (favor ortho), got {s}"


def test_discriminator_neutral_when_onset_density_unknown():
    pwp = _per_window_probs({
        "Cicada":      np.array([0.3, 0.3, 0.3, 0.3, 0.3]),
        "Grasshopper": np.array([0.3, 0.3, 0.3, 0.3, 0.3]),
    })
    s = discriminator_score(pwp, CLASSES, onset_density_per_sec=None)
    assert s == 0.0


# --- apply_gate: activation conditions ----------------------------------

def test_gate_inert_when_top1_is_bee():
    probs = _probs({"Bee": 0.6, "Beetle": 0.2, "Cricket": 0.1, "Grasshopper": 0.1})
    pwp = _per_window_probs({"Cicada": np.full(5, 0.3), "Grasshopper": np.full(5, 0.1)})
    new, fired, tel = apply_gate(probs, CLASSES, pwp, onset_density_per_sec=2.0)
    assert not fired
    assert np.allclose(new, probs)


def test_gate_inert_when_top2_outside_targets():
    probs = _probs({"Cicada": 0.5, "Cricket": 0.4, "Bee": 0.1})
    pwp = _per_window_probs({"Cicada": np.full(5, 0.5), "Cricket": np.full(5, 0.4)})
    new, fired, _ = apply_gate(probs, CLASSES, pwp, onset_density_per_sec=2.0)
    assert not fired
    assert np.allclose(new, probs)


def test_gate_inert_when_margin_exceeds_floor():
    probs = _probs({"Cicada": 0.70, "Grasshopper": 0.20, "Bee": 0.10})
    pwp = _per_window_probs({"Cicada": np.full(5, 0.7), "Grasshopper": np.full(5, 0.2)})
    new, fired, _ = apply_gate(probs, CLASSES, pwp, onset_density_per_sec=2.0)
    assert not fired
    assert np.allclose(new, probs)


def test_gate_inert_when_both_top2_same_group():
    probs = _probs({"Grasshopper": 0.45, "Locust": 0.40, "Cicada": 0.10, "Bee": 0.05})
    pwp = _per_window_probs({"Grasshopper": np.full(5, 0.45), "Locust": np.full(5, 0.4)})
    new, fired, _ = apply_gate(probs, CLASSES, pwp, onset_density_per_sec=2.0)
    assert not fired
    assert np.allclose(new, probs)


# --- apply_gate: firing path --------------------------------------------

def test_gate_fires_and_nudges_toward_cicada_when_tonal():
    probs = _probs({"Grasshopper": 0.42, "Cicada": 0.40, "Bee": 0.10, "Beetle": 0.08})
    pwp = _per_window_probs({
        "Cicada":      np.array([0.40, 0.40, 0.40, 0.40, 0.40]),
        "Grasshopper": np.array([0.10, 0.55, 0.10, 0.55, 0.10]),
    })
    new, fired, tel = apply_gate(probs, CLASSES, pwp, onset_density_per_sec=1.0)
    assert fired
    c_idx, g_idx = CLASSES.index("Cicada"), CLASSES.index("Grasshopper")
    assert new[c_idx] > probs[c_idx]
    assert new[g_idx] < probs[g_idx]
    assert (new[c_idx] - probs[c_idx]) <= GATE_NUDGE_CAP + 1e-6
    assert (probs[g_idx] - new[g_idx]) <= GATE_NUDGE_CAP + 1e-6


def test_gate_does_not_touch_other_class_probabilities():
    """Critical guard: Bee/Beetle/Cricket/Wasp/Non-biological probs MUST not change."""
    probs = _probs({"Grasshopper": 0.42, "Cicada": 0.40, "Bee": 0.10, "Beetle": 0.08})
    pwp = _per_window_probs({
        "Cicada":      np.array([0.40, 0.40, 0.40, 0.40, 0.40]),
        "Grasshopper": np.array([0.10, 0.55, 0.10, 0.55, 0.10]),
    })
    new, fired, _ = apply_gate(probs, CLASSES, pwp, onset_density_per_sec=1.0)
    assert fired
    for cls in ["Bee", "Beetle", "Cricket", "Wasp", "Non-biological"]:
        i = CLASSES.index(cls)
        assert new[i] == pytest.approx(probs[i], abs=1e-6), \
            f"{cls} probability changed: {probs[i]} → {new[i]}"


def test_gate_output_sums_to_one():
    probs = _probs({"Grasshopper": 0.42, "Cicada": 0.40, "Bee": 0.10, "Beetle": 0.08})
    pwp = _per_window_probs({
        "Cicada":      np.array([0.40, 0.40, 0.40, 0.40, 0.40]),
        "Grasshopper": np.array([0.10, 0.55, 0.10, 0.55, 0.10]),
    })
    new, _, _ = apply_gate(probs, CLASSES, pwp, onset_density_per_sec=1.0)
    assert new.sum() == pytest.approx(1.0, abs=1e-6)


def test_gate_idempotent_when_inputs_are_neutral():
    """Fix A5: real idempotence assertion. Both variance and onset terms zero
    out → discriminator returns 0 → no movement, NOT just ≤ cap."""
    probs = _probs({"Grasshopper": 0.42, "Cicada": 0.40, "Bee": 0.10, "Beetle": 0.08})
    pwp = _per_window_probs({
        "Cicada":      np.array([0.40, 0.40, 0.40, 0.40, 0.40]),  # var=0
        "Grasshopper": np.array([0.42, 0.42, 0.42, 0.42, 0.42]),  # var=0
    })
    # onset_density at neutral pivot (NEUTRAL_ONSET) → onset_term=0.
    # Variance term: var(ortho)-var(cicada) = 0-0 = 0. Discriminator=0. No nudge.
    from backend.ml.orthoptera_cicada_gate import NEUTRAL_ONSET
    new, fired, _ = apply_gate(probs, CLASSES, pwp,
                                onset_density_per_sec=NEUTRAL_ONSET)
    c_idx = CLASSES.index("Cicada")
    g_idx = CLASSES.index("Grasshopper")
    assert new[c_idx] == pytest.approx(probs[c_idx], abs=1e-6)
    assert new[g_idx] == pytest.approx(probs[g_idx], abs=1e-6)
