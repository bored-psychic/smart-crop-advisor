"""Tests for the bootstrap_ci helper in scripts/eval_acoustic.py.

The helper is used by the no-regression gate to attach 95% CIs to macro_f1
and per-class F1 so future readers (and a future CI-aware gate) can tell
"Wasp F1=0.50" from "Wasp F1=0.50 with [0.23, 0.77] noise". These tests
guard the two properties that matter for that usage:

  1. The CIs are deterministic for a fixed seed — baseline rewrites must
     not flap on identical input.
  2. CI width shrinks as the sample size grows — a sanity check that we
     are actually doing the bootstrap, not returning a constant.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


sklearn = pytest.importorskip("sklearn")  # noqa: F841 — sklearn pulls in f1_score


def _synthetic_labels(n: int, n_classes: int = 4, accuracy: float = 0.7, seed: int = 0):
    """Generate (y_true, y_pred, labels) with controllable expected accuracy.

    y_pred copies y_true at rate `accuracy`, and otherwise picks a uniformly
    random *other* class. This gives a per-class F1 distribution with real
    noise that the bootstrap should be able to detect.
    """
    rng = np.random.default_rng(seed)
    y_true = rng.integers(0, n_classes, size=n)
    flips = rng.random(size=n) > accuracy
    y_pred = y_true.copy()
    for i in np.where(flips)[0]:
        wrong = [c for c in range(n_classes) if c != y_true[i]]
        y_pred[i] = rng.choice(wrong)
    labels = np.arange(n_classes)
    return y_true, y_pred, labels


def test_bootstrap_ci_is_deterministic_for_fixed_seed():
    from scripts.eval_acoustic import bootstrap_ci
    y_true, y_pred, labels = _synthetic_labels(n=300, n_classes=4, accuracy=0.75)
    macro_a, per_a = bootstrap_ci(y_true, y_pred, labels, n_boot=200, seed=42)
    macro_b, per_b = bootstrap_ci(y_true, y_pred, labels, n_boot=200, seed=42)
    assert macro_a == macro_b
    assert per_a == per_b


def test_bootstrap_ci_width_shrinks_with_sample_size():
    # The whole point of CIs is to expose how much noise the test fold has.
    # If we pass more data through identical generative noise, the CI must
    # tighten — otherwise the helper isn't bootstrapping correctly.
    from scripts.eval_acoustic import bootstrap_ci
    y20_t, y20_p, labels = _synthetic_labels(n=20, n_classes=4, accuracy=0.75, seed=1)
    y2000_t, y2000_p, _ = _synthetic_labels(n=2000, n_classes=4, accuracy=0.75, seed=2)

    (lo_20, hi_20), _ = bootstrap_ci(y20_t, y20_p, labels, n_boot=500, seed=7)
    (lo_2k, hi_2k), _ = bootstrap_ci(y2000_t, y2000_p, labels, n_boot=500, seed=7)

    width_20 = hi_20 - lo_20
    width_2k = hi_2k - lo_2k
    # 100x more data should shrink the CI considerably; allow generous
    # headroom but reject "didn't shrink at all" failures.
    assert width_2k <= 0.30 * width_20, (
        f"CI did not tighten with n: n=20 width={width_20:.3f} "
        f"n=2000 width={width_2k:.3f}"
    )


def test_bootstrap_ci_brackets_point_estimate():
    # The point estimate of macro_f1 on the full sample should fall inside
    # the 95% CI most of the time. Not a strict bracketing guarantee (CIs
    # are estimated, not exact), but a useful regression check that the
    # helper isn't returning systematically off-center bounds.
    from sklearn.metrics import f1_score
    from scripts.eval_acoustic import bootstrap_ci
    y_true, y_pred, labels = _synthetic_labels(n=500, n_classes=4, accuracy=0.8, seed=3)
    point = f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0)
    (lo, hi), _ = bootstrap_ci(y_true, y_pred, labels, n_boot=500, seed=11)
    assert lo <= point <= hi, f"point {point:.3f} outside CI [{lo:.3f}, {hi:.3f}]"
