"""Unit tests for scripts/probe_orthoptera_cicada.py — mixer + label helpers."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.probe_orthoptera_cicada import (  # noqa: E402
    mix_at_snr,
    ortho_group,
)


def test_mix_at_snr_preserves_length():
    sr = 32000
    a = np.random.randn(sr * 2).astype(np.float32) * 0.1
    b = np.random.randn(sr * 2).astype(np.float32) * 0.1
    m = mix_at_snr(a, b, snr_db=5.0)
    assert m.shape == a.shape
    assert m.dtype == np.float32


def test_mix_at_snr_target_level():
    sr = 32000
    a = np.ones(sr, dtype=np.float32) * 0.5
    b = np.ones(sr, dtype=np.float32) * 0.5
    m = mix_at_snr(a, b, snr_db=0.0)
    rms_a = float(np.sqrt(np.mean(a**2)))
    scaled_b_rms = float(np.sqrt(np.mean((m - a) ** 2)))
    assert scaled_b_rms == pytest.approx(rms_a, rel=1e-3)


def test_ortho_group_classifies_orthoptera():
    assert ortho_group("Grasshopper") == "orthoptera"
    assert ortho_group("Locust") == "orthoptera"
    assert ortho_group("Cicada") == "cicada"
    assert ortho_group("Bee") is None
    assert ortho_group("Beetle") is None
