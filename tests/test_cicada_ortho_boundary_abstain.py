"""Cicada/Orthoptera boundary abstain elevation.

When the head's top-1 and top-2 span the cicada-vs-orthoptera boundary with
narrow margin, the head has a known confidently-wrong failure mode (probe
2026-05-25: Cicada→Grasshopper at top1≈0.55, top2-Cicada≈0.38, margin≈0.17).
The variance-driven tie-breaker gate was rejected (NULL_RESULT.md). Abstain
elevation defuses the same failure by demanding higher confidence to commit
on the boundary. Margin threshold (0.20) was tuned on probe data after a
first attempt at 0.15 caught zero of 19 cross-group errors.

Tests verify the elevation fires/holds in the intended cases and is inert
everywhere else.
"""
from __future__ import annotations

import numpy as np
import pytest

from backend.ml.panns_model import (
    PANNsAbstain,
    PANNsBundle,
    CICADA_ORTHO_BOUNDARY_TOP1_FLOOR,
    CICADA_ORTHO_BOUNDARY_MARGIN,
)


CLASSES = ["Bee", "Beetle", "Cicada", "Cricket", "Grasshopper", "Locust",
           "Non-biological", "Wasp"]


class _FakeLE:
    classes_ = np.array(CLASSES)

    def inverse_transform(self, idx_arr):
        return np.array([CLASSES[i] for i in idx_arr])


class _FakeClf:
    def __init__(self, probs_to_return):
        self._probs = probs_to_return
        self.classes_ = np.arange(len(CLASSES))

    def decision_function(self, feats):
        n = np.atleast_2d(feats).shape[0]
        logits = np.log(np.clip(self._probs, 1e-9, 1.0))
        return np.tile(logits, (n, 1))


class _FakeTagger:
    def inference(self, audio):
        n = audio.shape[0] if audio.ndim == 2 else 1
        return (np.random.rand(n, 527).astype(np.float32) * 0.01,
                np.random.rand(n, 2048).astype(np.float32) * 0.01)


def _make_bundle(probs_dict):
    probs = np.zeros(len(CLASSES), dtype=np.float32)
    for k, v in probs_dict.items():
        probs[CLASSES.index(k)] = v
    probs = probs / probs.sum()
    return PANNsBundle(
        audio_tagger=_FakeTagger(),
        clf=_FakeClf(probs),
        label_encoder=_FakeLE(),
        classes=CLASSES,
        test_accuracy=0.80,
        trained_at="test",
        temperature=1.0,
    )


def _pcm_2s(sr=32000):
    return np.random.randn(sr * 2).astype(np.float32) * 0.05


def test_constants_match_design():
    assert CICADA_ORTHO_BOUNDARY_TOP1_FLOOR == 0.65
    assert CICADA_ORTHO_BOUNDARY_MARGIN == 0.20


def test_boundary_abstains_when_top1_below_elevated_floor():
    # top1=Cicada (0.55), top2=Grasshopper (0.42), margin=0.13<0.20 → elevation
    # active. 0.55 < 0.65 floor → must abstain (default 0.45 would have let it
    # commit, which was the production failure mode).
    bundle = _make_bundle({"Cicada": 0.55, "Grasshopper": 0.42,
                            "Bee": 0.02, "Beetle": 0.01})
    with pytest.raises(PANNsAbstain):
        bundle.predict(_pcm_2s(), 32000)


# NOTE: there is no "commits when top1 above elevated floor" test because no
# such case is reachable. The boundary precondition requires margin < 0.20;
# combined with top1 + top2 ≤ 1.0 (probability simplex), this caps top1 at
# (1 + margin) / 2 < 0.60 — strictly below the 0.65 floor. So the elevation
# always forces abstain when the boundary fires. That is the intended product
# behavior: low-margin boundary cases route to API fallback. The boundary thus
# acts as an unconditional abstain switch within its narrow precondition.


def test_boundary_inert_when_margin_above_floor():
    # top1=Cicada (0.55), top2=Grasshopper (0.32), margin=0.23 ≥ 0.20 → no
    # elevation; default 0.45 floor applies → 0.55 > 0.45 → commit.
    bundle = _make_bundle({"Cicada": 0.55, "Grasshopper": 0.32,
                            "Bee": 0.07, "Beetle": 0.06})
    out = bundle.predict(_pcm_2s(), 32000)
    assert out["pest"] == "Cicada"


def test_boundary_inert_when_top2_outside_targets():
    # top1=Cicada (0.55), top2=Cricket (0.42), margin=0.13<0.20 BUT
    # Cricket not in {Cicada, Grasshopper, Locust} → no elevation.
    bundle = _make_bundle({"Cicada": 0.55, "Cricket": 0.42,
                            "Bee": 0.02, "Beetle": 0.01})
    out = bundle.predict(_pcm_2s(), 32000)
    assert out["pest"] == "Cicada"


def test_boundary_inert_when_top2_same_group_orthoptera():
    # Grasshopper+Locust = same group. No elevation; default floor applies.
    bundle = _make_bundle({"Grasshopper": 0.55, "Locust": 0.42,
                            "Bee": 0.02, "Beetle": 0.01})
    out = bundle.predict(_pcm_2s(), 32000)
    assert out["pest"] == "Grasshopper"


def test_boundary_inert_when_top1_is_bee():
    # Bee top1 — not in target set. No elevation. Default abstain rules apply.
    bundle = _make_bundle({"Bee": 0.55, "Cicada": 0.42,
                            "Beetle": 0.02, "Cricket": 0.01})
    out = bundle.predict(_pcm_2s(), 32000)
    assert out["pest"] == "Bee"


def test_boundary_locust_vs_cicada_also_elevates():
    # Locust top1 (0.55), Cicada top2 (0.42), margin=0.13<0.20 → elevation
    # active. Locust per-class floor is 0.35 (lower than default), but
    # boundary rule should take MAX so 0.65 wins. 0.55 < 0.65 → abstain.
    bundle = _make_bundle({"Locust": 0.55, "Cicada": 0.42,
                            "Bee": 0.02, "Beetle": 0.01})
    with pytest.raises(PANNsAbstain):
        bundle.predict(_pcm_2s(), 32000)


def test_boundary_cicada_top1_grasshopper_top2_reverse_direction():
    # Symmetric: Cicada top1, Grasshopper top2 already covered. This is the
    # mirror: Grasshopper top1 (0.55), Cicada top2 (0.42). Same group-span,
    # same margin — must abstain.
    bundle = _make_bundle({"Grasshopper": 0.55, "Cicada": 0.42,
                            "Bee": 0.02, "Beetle": 0.01})
    with pytest.raises(PANNsAbstain):
        bundle.predict(_pcm_2s(), 32000)


def test_boundary_inert_when_real_world_margin_017_caught():
    # Probe 2026-05-25 cicada error pattern: top1=Grasshopper 0.55, top2=Cicada
    # 0.38, margin=0.17. At the original margin=0.15 precondition this case
    # would have *missed* the boundary check (0.17 ≥ 0.15) and committed. At
    # the tuned margin=0.20, the boundary fires → top1 floor elevates → 0.55 <
    # 0.65 → abstain. Regression-locks the threshold tuning.
    bundle = _make_bundle({"Grasshopper": 0.55, "Cicada": 0.38,
                            "Bee": 0.04, "Beetle": 0.03})
    with pytest.raises(PANNsAbstain):
        bundle.predict(_pcm_2s(), 32000)
