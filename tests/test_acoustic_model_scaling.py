"""Pinning tests for the peak_bin scaling in _features_from_pcm.

Covers:
  - Length-1 array: argmax=0 → peak_bin=0 (no ZeroDivisionError).
  - Argmax at last element → peak_bin=15 (boundary maps exactly to 15).
  - Argmax at midpoint → expected scaled integer value.
"""
from __future__ import annotations

import numpy as np
import pytest

from backend.ml.acoustic_model import _features_from_pcm

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pcm_with_spike(rate: int, spike_freq_hz: float, duration_s: float = 2.0) -> np.ndarray:
    """Return mono PCM (float32) with energy concentrated at *spike_freq_hz*."""
    t = np.linspace(0, duration_s, int(rate * duration_s), endpoint=False, dtype=np.float32)
    return np.sin(2 * np.pi * spike_freq_hz * t).astype(np.float32)


def _peak_bin_from_pcm(pcm: np.ndarray, rate: int) -> float:
    """Extract only the peak_bin element (index 6) from _features_from_pcm."""
    features = _features_from_pcm(pcm, rate)
    assert features is not None, "_features_from_pcm returned None unexpectedly"
    return features[6]


# ---------------------------------------------------------------------------
# Boundary: single-element FFT array (length-1 input triggers edge case)
# ---------------------------------------------------------------------------

def test_peak_bin_single_element_no_zerodivision():
    """Array of length 1 → argmax=0 → peak_bin=0, no ZeroDivisionError."""
    rate = 16_000
    # Minimum PCM that passes the length guard (rate*0.5 samples), but we
    # fabricate fft_vals directly by passing a constant-value array so that
    # rfft produces a single dominant DC bin.
    # A constant signal (DC) has all energy in bin 0 → argmax = 0 → peak_bin = 0.
    pcm = np.ones(int(rate * 0.6), dtype=np.float32)
    peak = _peak_bin_from_pcm(pcm, rate)
    assert peak == 0.0, f"Expected 0.0 for DC signal, got {peak}"


# ---------------------------------------------------------------------------
# Boundary: argmax at the *last* FFT bin → must map to exactly 15
# ---------------------------------------------------------------------------

def test_peak_bin_last_bin_maps_to_15():
    """Energy at the Nyquist bin (last FFT bin) → peak_bin = 15.

    cos(2π·Nyquist·t) evaluated at the sample grid equals (-1)^n, which has
    all its energy at the very last rfft bin (index N//2).  That forces argmax
    to the last element and the scaling formula must return exactly 15.
    """
    rate = 16_000
    duration_s = 2.0
    n_samples = int(rate * duration_s)
    t = np.linspace(0, duration_s, n_samples, endpoint=False, dtype=np.float32)
    nyquist_hz = rate / 2
    # cos at Nyquist concentrates all spectral energy in the last rfft bin.
    pcm = np.cos(2 * np.pi * nyquist_hz * t).astype(np.float32)
    peak = _peak_bin_from_pcm(pcm, rate)
    assert peak == 15.0, f"Expected 15.0 for Nyquist cos signal, got {peak}"


# ---------------------------------------------------------------------------
# Known mid-range: energy at ~25 % of Nyquist → scaled peak_bin ≈ 3 or 4
# ---------------------------------------------------------------------------

def test_peak_bin_midrange_known_value():
    """Energy near 25 % of Nyquist → peak_bin in the expected range [3, 5]."""
    rate = 16_000
    # 2000 Hz is ~25 % of Nyquist (8000 Hz).
    target_hz = 2_000.0
    pcm = _make_pcm_with_spike(rate, target_hz)
    peak = _peak_bin_from_pcm(pcm, rate)
    # For a 4-second window at 16 kHz → len(seg)=64000 → fft_vals len=32001.
    # argmax ≈ round(2000 / (16000/64000)) = 8000.
    # peak_bin = clip(int(8000 * 15 / (32001 - 1)), 0, 15)
    #           = clip(int(8000 * 15 / 32000), 0, 15)
    #           = clip(int(3.75), 0, 15) = 3
    assert 3 <= peak <= 5, f"Expected peak_bin in [3, 5] for 2 kHz signal, got {peak}"


# ---------------------------------------------------------------------------
# Clip safety: ensure result is always in [0, 15] regardless of input
# ---------------------------------------------------------------------------

def test_peak_bin_always_in_valid_range():
    """peak_bin must be in [0.0, 15.0] for a range of synthetic signals."""
    rate = 16_000
    test_freqs = [100, 500, 1000, 2000, 4000, 7999]
    for freq in test_freqs:
        pcm = _make_pcm_with_spike(rate, freq)
        peak = _peak_bin_from_pcm(pcm, rate)
        assert 0.0 <= peak <= 15.0, (
            f"peak_bin={peak} out of [0, 15] for spike at {freq} Hz"
        )
