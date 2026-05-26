"""Unit tests for the bandpass + energy normalization pre-filter.

The helper lives in `backend.services.acoustic.dsp` and is called by the
PANNs inference path (`backend.ml.panns_model.PANNsBundle.predict`) and the
training script (`scripts/train_panns_head.cached_embed`) before the audio
reaches CNN14. The pre-filter is gated by `Settings.ENABLE_BANDPASS_FILTER`
at the call sites — these tests exercise the helper itself, not the flag
wiring (the wiring is exercised by leaving the flag at its default `False`
and letting the existing acoustic-pipeline tests run unchanged).

Cutoffs: 1 kHz HP, 15 kHz LP, Butterworth order 4. Targets cricket
stridulation (2–8 kHz), grasshopper broadband (3–10 kHz), cicada (4–7 kHz)
while removing sub-kHz wind/motor rumble and >15 kHz hiss.
"""
from __future__ import annotations

import numpy as np
import pytest

from backend.services.acoustic.dsp import (
    bandpass_and_energy_normalize,
    bandpass_filter_enabled,
)


SAMPLE_RATE = 32000  # CNN14 native rate; helper is called at this rate.


def _band_energy_db(pcm: np.ndarray, rate: int, lo: float, hi: float) -> float:
    """Mean log-magnitude (dB) of the FFT bins within [lo, hi] Hz."""
    fft_mag = np.abs(np.fft.rfft(pcm.astype(np.float64)))
    freqs = np.fft.rfftfreq(pcm.size, 1.0 / rate)
    mask = (freqs >= lo) & (freqs < hi)
    if not mask.any():
        return -np.inf
    mean_mag = float(np.mean(fft_mag[mask]))
    return 20.0 * np.log10(max(mean_mag, 1e-12))


def _sine(rate: int, freq_hz: float, seconds: float, amp: float = 0.3) -> np.ndarray:
    t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
    return (amp * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)


def test_bandpass_suppresses_subkhz_relative_to_inband() -> None:
    """White noise has equal energy across all bands. After bandpass +
    energy-norm, the in-band (2–8 kHz) energy dominates the RMS scaling,
    so sub-1 kHz content stays heavily attenuated relative to in-band.

    Energy normalization restores any non-zero signal to unit RMS, so
    absolute attenuation against a pure sub-band tone is meaningless
    (post-norm RMS would be reset to ~1 from whatever leakage survived).
    The honest measurement is the RELATIVE attenuation across bands on
    a signal with substantial in-band energy.
    """
    rng = np.random.default_rng(0)
    pcm = (0.3 * rng.standard_normal(SAMPLE_RATE * 2)).astype(np.float32)

    in_band_before = _band_energy_db(pcm, SAMPLE_RATE, 2000.0, 8000.0)
    sub_band_before = _band_energy_db(pcm, SAMPLE_RATE, 100.0, 400.0)

    out = bandpass_and_energy_normalize(pcm, SAMPLE_RATE)
    in_band_after = _band_energy_db(out, SAMPLE_RATE, 2000.0, 8000.0)
    sub_band_after = _band_energy_db(out, SAMPLE_RATE, 100.0, 400.0)

    # In-band energy ratio (after-before) should be roughly the same as
    # the global RMS rescaling. Sub-band ratio should be 40+ dB lower
    # than in-band ratio, because sub-band content was attenuated by the
    # filter before the rescaling.
    in_band_ratio = in_band_after - in_band_before
    sub_band_ratio = sub_band_after - sub_band_before
    relative_attenuation = in_band_ratio - sub_band_ratio

    assert relative_attenuation > 40.0, (
        f"sub-band relative attenuation only {relative_attenuation:.1f} dB "
        f"(need > 40); in-band Δ={in_band_ratio:.1f}, "
        f"sub-band Δ={sub_band_ratio:.1f}"
    )


def test_bandpass_suppresses_above_15khz_relative_to_inband() -> None:
    """Same relative-attenuation test for the > 15 kHz stop-band.

    Bound is looser than the sub-kHz case because the LP cutoff (15 kHz)
    sits closer to Nyquist (16 kHz at 32 kHz sample rate), giving the
    Butterworth less roll-off room.
    """
    rng = np.random.default_rng(1)
    pcm = (0.3 * rng.standard_normal(SAMPLE_RATE * 2)).astype(np.float32)

    in_band_before = _band_energy_db(pcm, SAMPLE_RATE, 2000.0, 8000.0)
    high_band_before = _band_energy_db(pcm, SAMPLE_RATE, 15500.0, 16000.0)

    out = bandpass_and_energy_normalize(pcm, SAMPLE_RATE)
    in_band_after = _band_energy_db(out, SAMPLE_RATE, 2000.0, 8000.0)
    high_band_after = _band_energy_db(out, SAMPLE_RATE, 15500.0, 16000.0)

    in_band_ratio = in_band_after - in_band_before
    high_band_ratio = high_band_after - high_band_before
    relative_attenuation = in_band_ratio - high_band_ratio

    assert relative_attenuation > 20.0, (
        f">15 kHz relative attenuation only {relative_attenuation:.1f} dB "
        f"(need > 20); in-band Δ={in_band_ratio:.1f}, "
        f"high-band Δ={high_band_ratio:.1f}"
    )


def test_bandpass_preserves_in_band_tone() -> None:
    """An 8 kHz sine (mid-band) survives the bandpass; the dominant FFT bin
    after filtering is still in [7.5, 8.5] kHz."""
    pcm = _sine(SAMPLE_RATE, 8000.0, seconds=1.0, amp=0.5)
    out = bandpass_and_energy_normalize(pcm, SAMPLE_RATE)

    fft_mag = np.abs(np.fft.rfft(out.astype(np.float64)))
    freqs = np.fft.rfftfreq(out.size, 1.0 / SAMPLE_RATE)
    peak_freq = float(freqs[int(np.argmax(fft_mag))])

    assert 7500.0 <= peak_freq <= 8500.0, (
        f"8 kHz tone shifted to {peak_freq:.0f} Hz after filtering"
    )


def test_dc_offset_is_removed() -> None:
    """A DC + 5 kHz signal has its DC component removed (the 1 kHz HP
    handles the entire sub-Hz to 1 kHz band, DC included)."""
    pcm = _sine(SAMPLE_RATE, 5000.0, seconds=1.0, amp=0.3) + 0.4
    assert abs(float(np.mean(pcm))) > 0.3  # confirm fixture has DC

    out = bandpass_and_energy_normalize(pcm, SAMPLE_RATE)

    assert abs(float(np.mean(out))) < 0.05, (
        f"DC residual {float(np.mean(out)):.3f} after filter"
    )


def test_output_rms_is_consistent_across_input_levels() -> None:
    """Normalization removes a large degree of freedom — widely-varied
    input amplitudes converge to a small post-norm RMS range. Pure sines
    have crest factor √2 so the peak-cap stage scales them to peak=1,
    giving RMS = 1/√2 ≈ 0.707; the assertion bound is [0.4, 1.0] to
    cover both pure-tone and noisier inputs."""
    rmses = []
    for amp in (0.01, 0.1, 0.5, 0.9):
        pcm = _sine(SAMPLE_RATE, 5000.0, seconds=1.0, amp=amp)
        out = bandpass_and_energy_normalize(pcm, SAMPLE_RATE)
        rms = float(np.sqrt(np.mean(out.astype(np.float64) ** 2)))
        rmses.append(rms)
        assert 0.4 <= rms <= 1.0, (
            f"amp={amp}: post-norm RMS {rms:.3f} outside [0.4, 1.0]"
        )
    # And the spread is tight — different input amps don't fan out post-norm.
    assert max(rmses) - min(rmses) < 0.05, (
        f"post-norm RMS spread {max(rmses) - min(rmses):.3f} > 0.05"
    )


def test_output_stays_in_pcm_range() -> None:
    """Energy normalization clips to ±1.0 so downstream code that assumes
    [-1, 1] float PCM (CNN14, WAV encode) does not see out-of-range
    samples even when the pre-norm signal had extreme dynamic range."""
    rng = np.random.default_rng(42)
    pcm = (0.8 * rng.standard_normal(SAMPLE_RATE)).astype(np.float32)
    out = bandpass_and_energy_normalize(pcm, SAMPLE_RATE)
    assert float(np.max(np.abs(out))) <= 1.0 + 1e-6, (
        f"peak {float(np.max(np.abs(out))):.3f} exceeds [-1, 1]"
    )


def test_output_is_float32() -> None:
    """CNN14 / panns_inference expects float32; the helper must not
    silently upcast to float64 (doubles memory, can break torch dtype
    checks downstream)."""
    pcm = _sine(SAMPLE_RATE, 5000.0, seconds=1.0, amp=0.5)
    out = bandpass_and_energy_normalize(pcm, SAMPLE_RATE)
    assert out.dtype == np.float32, f"got {out.dtype}, expected float32"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("0", False),
        ("", False),
        ("no", False),
        ("anything-else", False),
    ],
)
def test_flag_reader_parses_env_var(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: bool,
) -> None:
    """The pre-filter flag is read from ENABLE_BANDPASS_FILTER directly
    (not via pydantic Settings) so the hot path doesn't drag in the full
    boot-config validation. This test pins the truthy/falsy parsing."""
    monkeypatch.setenv("ENABLE_BANDPASS_FILTER", value)
    assert bandpass_filter_enabled() is expected


def test_flag_reader_defaults_false_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unset env var → flag off. Ship default; safety net against ambient
    env leak from the user's shell promoting the flag without intent."""
    monkeypatch.delenv("ENABLE_BANDPASS_FILTER", raising=False)
    assert bandpass_filter_enabled() is False


def test_handles_silent_input_without_crashing() -> None:
    """A nearly-silent buffer (RMS ≈ 0) must not divide-by-zero in the
    energy norm step. The MIN_RMS=1e-4 silence check upstream in the
    pipeline catches true silence; the helper should still be safe if
    called with very quiet audio (e.g. during training on a borderline
    clip that passed librosa.load but is mostly zeros)."""
    pcm = np.zeros(SAMPLE_RATE, dtype=np.float32)
    out = bandpass_and_energy_normalize(pcm, SAMPLE_RATE)
    assert out.shape == pcm.shape
    assert np.all(np.isfinite(out))
