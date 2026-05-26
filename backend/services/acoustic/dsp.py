"""DSP helpers for the acoustic pipeline.

Audio decode/encode, LUFS normalization, framed-RMS SNR + onset density,
band-energy summarization, and mel-spectrogram PNG rendering. Pure
signal-processing — no ML, no I/O, no FastAPI.
"""

import importlib
import io
import os
from typing import Optional

import numpy as np
import scipy.io.wavfile as wav
from PIL import Image


def bandpass_filter_enabled() -> bool:
    """Read the ENABLE_BANDPASS_FILTER env var.

    The flag bypasses pydantic-settings (see backend/config.py rationale)
    so the hot path doesn't force a full Settings instantiation that
    fails in tests / training scripts without the API_KEY / JWT_SECRET
    boot env. Accepts "1", "true", "yes", "on" (case-insensitive) as
    truthy; anything else (including unset) is false.
    """
    return os.environ.get("ENABLE_BANDPASS_FILTER", "").lower() in (
        "1", "true", "yes", "on",
    )


def _decode_audio(audio_bytes: bytes) -> tuple[Optional[np.ndarray], int, Optional[str]]:
    """
    Decode audio to mono float32 PCM in [-1, 1].
    Returns (pcm, sample_rate, method) or (None, 0, None) on failure.
    method is 'scipy_wav' or 'pydub_ffmpeg'.
    """
    try:
        rate, data = wav.read(io.BytesIO(audio_bytes))
        pcm = _to_mono_float(data)
        return _normalize_lufs(pcm, int(rate)), int(rate), "scipy_wav"
    except Exception:
        pass

    try:
        audio_segment = importlib.import_module("pydub").AudioSegment
        seg = audio_segment.from_file(io.BytesIO(audio_bytes))
        seg = seg.set_channels(1)
        rate = int(seg.frame_rate)
        sw = seg.sample_width
        samples = np.array(seg.get_array_of_samples())
        if sw == 2:
            pcm = samples.astype(np.float32) / 32768.0
        elif sw == 4:
            pcm = samples.astype(np.float32) / 2147483648.0
        elif sw == 1:
            pcm = (samples.astype(np.float32) - 128.0) / 128.0
        else:
            pcm = samples.astype(np.float32)
        return _normalize_lufs(pcm, rate), rate, "pydub_ffmpeg"
    except Exception:
        return None, 0, None


def _to_mono_float(data: np.ndarray) -> np.ndarray:
    if data.ndim > 1:
        # Average channels rather than picking ch0 — preserves signal when one
        # channel is dead (some phone mics record silence on the second
        # channel) and avoids halving SNR on healthy stereo recordings.
        channel_rms = [
            float(np.sqrt(np.mean(data[:, c].astype(np.float32) ** 2)))
            for c in range(data.shape[1])
        ]
        if max(channel_rms) > 0 and min(channel_rms) < 1e-6:
            live = int(np.argmax(channel_rms))
            data = data[:, live]
        else:
            data = data.mean(axis=1)
    if data.dtype == np.int16:
        return data.astype(np.float32) / 32768.0
    if data.dtype == np.int32:
        return data.astype(np.float32) / 2147483648.0
    if data.dtype == np.uint8:
        return (data.astype(np.float32) - 128.0) / 128.0
    return data.astype(np.float32)


def _normalize_lufs(pcm: np.ndarray, rate: int, target_lufs: float = -23.0) -> np.ndarray:
    """Normalize PCM to target integrated loudness (LUFS).

    Skips normalization when the clip is too quiet/short to measure (silence,
    sub-second clips). Clipping guard ensures the output stays in [-1, 1].
    """
    try:
        import pyloudnorm as pyln
    except ImportError:
        return pcm
    meter = pyln.Meter(rate)
    loudness = meter.integrated_loudness(pcm)
    if not np.isfinite(loudness) or loudness < -70.0:
        return pcm
    gain_linear = 10.0 ** ((target_lufs - loudness) / 20.0)
    normalized = (pcm * gain_linear).astype(np.float32)
    peak = np.abs(normalized).max()
    if peak > 0.99:
        normalized *= 0.99 / peak
    return normalized


_BANDPASS_LO_HZ = 1000.0
_BANDPASS_HI_HZ = 15000.0
_BANDPASS_ORDER = 4


def bandpass_and_energy_normalize(pcm: np.ndarray, rate: int) -> np.ndarray:
    """Butterworth bandpass 1–15 kHz + per-channel energy normalization.

    SNR is the dominant error source for insect-audio classification:
    sub-1 kHz wind/motor/handling rumble and >15 kHz hiss carry no insect
    signal but shift the learned-feature distribution at inference time.
    The passband retains cricket stridulation (2–8 kHz), grasshopper
    broadband (3–10 kHz), and cicada (4–7 kHz).

    Applied identically at training (scripts/train_panns_head.cached_embed,
    post-augmentation) and inference (backend.ml.panns_model.PANNsBundle.
    predict, post-resample). The pre-filter is feature-flagged via
    Settings.ENABLE_BANDPASS_FILTER at each call site; this helper itself
    is unconditional and pure.

    Energy normalization (divide by RMS, clip to [-1, 1]) follows the
    bandpass so the post-filter signal lands at unit RMS regardless of the
    pre-filter loudness — removes a degree of freedom the head would
    otherwise have to learn around.
    """
    from scipy.signal import butter, sosfiltfilt

    pcm = pcm.astype(np.float32, copy=False)
    if pcm.size == 0:
        return pcm

    nyquist = rate / 2.0
    lo = _BANDPASS_LO_HZ / nyquist
    hi = min(_BANDPASS_HI_HZ, nyquist * 0.99) / nyquist
    if not (0.0 < lo < hi < 1.0):
        return pcm
    sos = butter(_BANDPASS_ORDER, [lo, hi], btype="band", output="sos")
    filtered = sosfiltfilt(sos, pcm).astype(np.float32, copy=False)

    rms = float(np.sqrt(np.mean(filtered.astype(np.float64) ** 2)))
    if rms < 1e-9:
        return filtered
    # Two-stage scale: first to unit RMS, then back off if the peak exceeds
    # ±1 so the output fits the [-1, 1] PCM convention. Hard-clipping would
    # introduce broadband distortion harmonics that defeat the bandpass —
    # the stop-band fills back in with intermodulation products. Linear
    # scale-down preserves the spectrum; the final RMS may be < 1 for
    # high-crest signals (pure tones land at ~1/√2).
    normalized = filtered / rms
    peak = float(np.max(np.abs(normalized)))
    if peak > 1.0:
        normalized = normalized / peak
    return normalized.astype(np.float32, copy=False)


def _encode_wav(pcm: np.ndarray, rate: int) -> bytes:
    """Encode mono float32 PCM in [-1, 1] to a 16-bit WAV byte string.

    Inverse of `_decode_audio`. Used to hand Gemini a clean, supported MIME
    (audio/wav) carrying only the truncated analysis window — same data the
    rest of the pipeline reasons over.
    """
    int16 = np.clip(pcm * 32767.0, -32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    wav.write(buf, rate, int16)
    return buf.getvalue()


def _snr_and_onsets(seg: np.ndarray, rate: int) -> dict:
    """Estimate signal-to-noise ratio (dB) and onset density (onsets/sec).

    SNR uses framed RMS — signal = 90th percentile, noise floor = 10th
    percentile. This is robust to short bursts and silences. Onset density
    is a useful prior for distinguishing chewing/stridulation (high onset
    rate) from sustained tonal sounds like bee hum or mechanical noise
    (very low onset rate).
    """
    try:
        import librosa
    except Exception:
        return {"snr_db": None, "onset_density_per_sec": None}

    frame = 2048
    hop = 512
    rms = librosa.feature.rms(y=seg.astype(np.float32, copy=False),
                              frame_length=frame, hop_length=hop)[0]
    if rms.size < 4:
        snr_db = None
    else:
        signal = float(np.percentile(rms, 90))
        noise = float(np.percentile(rms, 10))
        snr_db = round(20.0 * np.log10(max(signal, 1e-9) / max(noise, 1e-9)), 2)

    try:
        onsets = librosa.onset.onset_detect(
            y=seg.astype(np.float32, copy=False), sr=rate, units="time",
        )
        duration = len(seg) / rate if rate else 0.0
        density = round(float(len(onsets)) / duration, 3) if duration > 0 else 0.0
    except Exception:
        density = None

    # Weather noise heuristic: high spectral flatness (wind/rain ≈ white noise)
    # and low onset density both point to non-biological noise.
    # low_ratio (sub-500 Hz dominance) only contributes when flatness is ALSO
    # elevated — insects (locusts, grasshoppers) have strong low-freq wingbeats
    # that are TONAL, not flat; treating them as wind causes false Non-biological
    # predictions. Wind is both flat AND low-freq heavy; insect wings are only
    # the latter.
    try:
        seg_f = seg.astype(np.float32, copy=False)
        flatness = float(np.mean(librosa.feature.spectral_flatness(y=seg_f)))
        fft_mag = np.abs(np.fft.rfft(seg_f))
        freqs = np.fft.rfftfreq(len(seg_f), 1.0 / rate)
        low_energy = fft_mag[freqs < 500].mean() if (freqs < 500).any() else 0.0
        total_energy = fft_mag.mean() or 1e-9
        low_ratio = float(low_energy / total_energy)
        onset_score = max(0.0, 1.0 - ((density or 0.0) / 3.0))
        flatness_norm = min(flatness * 4, 1.0)
        # Joint signal: only penalise for low-freq dominance when the spectrum
        # is also flat (wind/rain). A tonal wingbeat scores high low_ratio but
        # low flatness → near-zero joint, avoiding false noise classification.
        low_ratio_penalty = low_ratio * flatness_norm
        weather_noise_score = round(
            0.5 * flatness_norm +
            0.3 * onset_score +
            0.2 * low_ratio_penalty,
            3,
        )
    except Exception:
        weather_noise_score = 0.0

    return {
        "snr_db": snr_db,
        "onset_density_per_sec": density,
        "weather_noise_score": weather_noise_score,
    }


def _band_energies(seg: np.ndarray, rate: int) -> dict:
    fft_vals = np.abs(np.fft.rfft(seg))
    freqs = np.fft.rfftfreq(len(seg), 1.0 / rate)

    def _band(lo: float, hi: float) -> float:
        mask = (freqs >= lo) & (freqs < hi)
        return float(np.mean(fft_vals[mask])) if mask.any() else 0.0

    return {
        '50-200 Hz':    round(_band(50, 200), 4),
        '200-500 Hz':   round(_band(200, 500), 4),
        '500-1200 Hz':  round(_band(500, 1200), 4),
        '1200-4000 Hz': round(_band(1200, 4000), 4),
    }


def _spectrogram_png(seg: np.ndarray, rate: int) -> bytes:
    """Render a mel-spectrogram PNG directly via librosa + PIL (no matplotlib).

    Output is a single-channel inferno-mapped image, top = high freq.
    """
    import librosa

    fmax = min(8000, rate // 2)
    mel = librosa.feature.melspectrogram(
        y=seg.astype(np.float32, copy=False),
        sr=rate, n_fft=512, hop_length=256, n_mels=128, fmax=fmax,
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)

    # Normalize to 0..1
    lo, hi = float(log_mel.min()), float(log_mel.max())
    norm = (log_mel - lo) / (hi - lo + 1e-9)
    # Flip so high freq is on top
    norm = norm[::-1, :]

    # Apply a coarse inferno-like RGB lookup (purple→orange→yellow).
    x = norm
    r = np.clip(1.5 * x - 0.2, 0, 1)
    g = np.clip(1.7 * x - 0.8, 0, 1)
    b = np.clip(0.4 + 0.9 * np.sin(np.pi * x) - 0.5 * x, 0, 1)
    rgb = (np.stack([r, g, b], axis=-1) * 255.0).astype(np.uint8)

    img = Image.fromarray(rgb, mode='RGB')
    # Upscale a bit so downstream consumers get a reasonable PNG.
    img = img.resize((max(640, rgb.shape[1] * 4), 320), Image.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()
