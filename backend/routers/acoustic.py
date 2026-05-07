"""Acoustic pest detection router."""

import base64
import importlib
import io
import json
from typing import Optional

import numpy as np
import scipy.io.wavfile as wav
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File, Form
from backend.schemas.acoustic import AcousticResponse
from backend.ml.acoustic_model import _features_from_pcm, _normalize_crop_type
from backend.auth import require_api_key
from backend.config import get_settings
from backend.core.constants import PEST_META

router = APIRouter(prefix="/api/acoustic", tags=["Acoustic Pest Detection"])

PEST_ICONS = {name: meta['icon'] for name, meta in PEST_META.items()}

MAX_ANALYSIS_SECONDS = 10
MIN_ANALYSIS_SECONDS = 1.5
MIN_RMS = 1e-4

METHODOLOGY_NOTE = (
    "Exploratory tool. Acoustic pest detection from spectrograms is an "
    "experimental signal — confirm pest identification by visual inspection "
    "before applying chemicals."
)


def _decode_audio(audio_bytes: bytes) -> tuple[Optional[np.ndarray], int, Optional[str]]:
    """
    Decode audio to mono float32 PCM in [-1, 1].
    Returns (pcm, sample_rate, method) or (None, 0, None) on failure.
    method is 'scipy_wav' or 'pydub_ffmpeg'.
    """
    try:
        rate, data = wav.read(io.BytesIO(audio_bytes))
        return _to_mono_float(data), int(rate), "scipy_wav"
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
        return pcm, rate, "pydub_ffmpeg"
    except Exception:
        return None, 0, None


def _to_mono_float(data: np.ndarray) -> np.ndarray:
    if data.ndim > 1:
        data = data[:, 0]
    if data.dtype == np.int16:
        return data.astype(np.float32) / 32768.0
    if data.dtype == np.int32:
        return data.astype(np.float32) / 2147483648.0
    if data.dtype == np.uint8:
        return (data.astype(np.float32) - 128.0) / 128.0
    return data.astype(np.float32)


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
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.specgram(seg, Fs=rate, cmap='inferno', NFFT=512, noverlap=256)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Frequency (Hz)')
    ax.set_ylim(0, min(8000, rate // 2))
    ax.set_title('Field Audio Spectrogram')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=80, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.read()


async def _claude_acoustic(spec_bytes: bytes, crop_type: str) -> Optional[dict]:
    try:
        from anthropic import AsyncAnthropic
        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            return None
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        img_b64 = base64.standard_b64encode(spec_bytes).decode()
        model_candidates = ["claude-sonnet-4-6"]
        for model_name in model_candidates:
            try:
                resp = await client.messages.create(
                    model=model_name,
                    max_tokens=600,
                    system=[{
                        "type": "text",
                        "text": (
                            "You are an expert bioacoustics analyst for crop pest detection. "
                            "Analyze spectrogram images of field audio recordings and identify pest signatures.\n\n"
                            "Known pest signatures in spectrograms:\n"
                            "- Healthy Plant: flat noise floor, low energy across all bands\n"
                            "- Aphid Colony: clustered mid-frequency bursts 200-400 Hz\n"
                            "- Whitefly Infestation: wing-beat harmonic series 400-700 Hz\n"
                            "- Locust Activity: high-amplitude low-frequency pulses 50-200 Hz\n"
                            "- Stem Borer: rhythmic low-frequency gnawing 50-150 Hz\n"
                            "- Early Fungal Infection: high-frequency crackling 800-1200 Hz\n"
                            "- Spider Mite: ultra-high-frequency scratching 1200-4000 Hz\n"
                            "- Thrips Infestation: rapid mid-frequency staccato 350-500 Hz\n\n"
                            "CALIBRATION RULES:\n"
                            "1. Spectrogram analysis is exploratory; you are not trained on labelled "
                            "spectrograms — be conservative.\n"
                            "2. If the signature is ambiguous, weak, or could be ambient noise, "
                            "set pest='Healthy Plant' and explain in action.\n"
                            "3. Confidence MUST be ≤ 70 unless the signature is textbook and "
                            "unambiguous (a clear concentrated band matching a profile above).\n"
                            "4. For weak or partial matches, use confidence 30-55.\n"
                            "5. Use the supplied crop type to favour ecologically plausible pests.\n\n"
                            "Respond ONLY with valid JSON, no markdown fences:\n"
                            '{"pest":"name","severity":"high|medium|low","freq_range":"e.g. 50-150 Hz",'
                            '"pattern":"describe what you see in spectrogram",'
                            '"energy_level":"Very High|High|Moderate|Low-moderate|Background",'
                            '"confidence":<int 0-100>,"action":"specific actionable advice for Indian farmer",'
                            '"top3":[["Pest1",85],["Pest2",10],["Pest3",5]]}'
                        ),
                        "cache_control": {"type": "ephemeral"},
                    }],
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    f"Crop: {crop_type}. Analyze this field audio spectrogram "
                                    "for pest signatures. Respond with JSON only."
                                ),
                            },
                        ],
                    }],
                )
                text = resp.content[0].text.strip()
                if text.startswith("```"):
                    text = text.strip("`")
                    if text.lower().startswith("json"):
                        text = text[4:].lstrip()
                return json.loads(text)
            except Exception:
                continue
        return None
    except Exception:
        return None


_VALID_PESTS = set(PEST_META.keys())
# Below this threshold we'd rather defer to the RF + crop priors than trust a
# weak Claude guess. Claude's own calibration rules cap weak matches at 30-55,
# so 25 lets confident-enough vision picks through while filtering noise.
_CLAUDE_MIN_CONFIDENCE = 25


def _coerce_claude_prediction(raw: Optional[dict]) -> Optional[dict]:
    """Validate Claude's JSON; return a schema-ready dict or None on any issue."""
    if not isinstance(raw, dict):
        return None

    pest = str(raw.get("pest", "")).strip()
    if pest not in _VALID_PESTS:
        return None

    try:
        confidence = int(round(float(raw.get("confidence", 0))))
    except (TypeError, ValueError):
        return None
    if confidence < _CLAUDE_MIN_CONFIDENCE:
        return None

    meta = PEST_META[pest]

    raw_top3 = raw.get("top3") or []
    cleaned_top3: list[tuple[str, int]] = []
    if isinstance(raw_top3, list):
        for entry in raw_top3[:3]:
            try:
                name = str(entry[0])
                score = int(round(float(entry[1])))
            except (TypeError, ValueError, IndexError):
                continue
            if name in _VALID_PESTS:
                cleaned_top3.append((name, max(0, min(100, score))))
    if not cleaned_top3:
        cleaned_top3 = [(pest, max(0, min(100, confidence)))]

    action = raw.get("action")
    action_str = str(action).strip() if action else ""

    return {
        "pest": pest,
        "severity": str(raw.get("severity") or meta["severity"]),
        "freq_range": str(raw.get("freq_range") or meta["freq_range"]),
        "pattern": str(raw.get("pattern") or meta["pattern"]),
        "energy_level": str(raw.get("energy_level") or meta["energy_level"]),
        "confidence": max(0, min(100, confidence)),
        "action": action_str or meta["action"],
        "icon": meta["icon"],
        "top3": cleaned_top3,
        "claude_advice": action_str or None,
    }


def _rejected(reason: str, warnings: list[str], duration: float, sr: int,
              decode: Optional[str]) -> AcousticResponse:
    return AcousticResponse(
        pest='Analysis Rejected',
        severity='low',
        confidence=0,
        freq_range='N/A',
        pattern='N/A',
        energy_level='N/A',
        action=reason,
        icon='⚠️',
        top3=[],
        ml_used=False,
        analysis_method='rejected',
        decode_method=decode,
        duration_seconds=round(duration, 2),
        analyzed_seconds=0.0,
        sample_rate=sr,
        quality_warnings=warnings,
        methodology_note=METHODOLOGY_NOTE,
    )


@router.post("/analyze", response_model=AcousticResponse)
async def analyze_audio(
    request: Request,
    file: UploadFile = File(..., description="Field audio recording (WAV/MP3/OGG)"),
    crop_type: str = Form("Unknown"),
    _: str = Depends(require_api_key),
):
    """Analyze audio for pest signatures — Claude bioacoustics first, RF fallback."""
    normalized_crop = _normalize_crop_type(crop_type)
    contents = await file.read()
    if not contents:
        return _rejected("Empty upload — no audio data received.", ["empty_upload"], 0.0, 0, None)

    pcm, rate, decode_method = _decode_audio(contents)
    if pcm is None:
        return _rejected(
            "Could not decode audio. WAV is supported natively; MP3/M4A/OGG require "
            "ffmpeg+pydub on the server (try uploading a WAV).",
            ["decode_failed"], 0.0, 0, None,
        )

    duration = len(pcm) / rate if rate else 0.0

    warnings: list[str] = []
    if duration < MIN_ANALYSIS_SECONDS:
        return _rejected(
            f"Recording is only {duration:.1f}s; need at least {MIN_ANALYSIS_SECONDS}s. "
            "Record 4–10s of steady ambient field audio and try again.",
            ["too_short"], duration, rate, decode_method,
        )

    rms = float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2))) if len(pcm) else 0.0
    if rms < MIN_RMS:
        return _rejected(
            "Recording is essentially silent. Move the phone closer to the crop "
            "and re-record.",
            ["below_noise_floor"], duration, rate, decode_method,
        )

    truncated = duration > MAX_ANALYSIS_SECONDS
    if truncated:
        warnings.append("truncated_to_10s")
        seg = pcm[:rate * MAX_ANALYSIS_SECONDS]
    else:
        seg = pcm

    if rate < 8000:
        warnings.append(f"low_sample_rate_{rate}Hz")
    if rate > 48000:
        warnings.append(f"high_sample_rate_{rate}Hz")

    band_energy = _band_energies(seg, rate)

    try:
        spec_bytes = _spectrogram_png(seg, rate)
    except Exception:
        spec_bytes = None

    base_meta = {
        'decode_method': decode_method,
        'truncated': truncated,
        'analyzed_seconds': round(min(duration, MAX_ANALYSIS_SECONDS), 2),
        'duration_seconds': round(duration, 2),
        'sample_rate': rate,
        'quality_warnings': warnings,
        'band_energy': band_energy,
        'methodology_note': METHODOLOGY_NOTE,
    }

    features = _features_from_pcm(seg, rate)
    if features is None:
        return _rejected(
            "Could not extract features from decoded audio.",
            warnings + ["feature_extract_failed"],
            duration, rate, decode_method,
        )

    # Claude vision is the primary classifier. The synthetic-trained Random
    # Forest ([backend/ml/acoustic_model.py]) only generalizes to two classes
    # (Spider Mite / Healthy) on real audio, so it now serves as an offline
    # fallback for when ANTHROPIC_API_KEY is missing or Claude returns
    # malformed / low-confidence JSON.
    claude_result = None
    if spec_bytes is not None:
        claude_result = await _claude_acoustic(spec_bytes, normalized_crop)
    claude_pred = _coerce_claude_prediction(claude_result)

    if claude_pred is not None:
        result = claude_pred
        result["ml_used"] = False
        result["analysis_method"] = "claude_vision"
        result["cv_accuracy"] = None
        result["cv_label"] = None
    else:
        warnings.append("claude_unavailable_or_invalid_response")
        acoustic_bundle = request.app.state.acoustic_model
        if acoustic_bundle is None:
            raise HTTPException(status_code=503, detail="Acoustic model unavailable")
        result = acoustic_bundle.predict(features, crop_type=normalized_crop)
        result["analysis_method"] = "random_forest"

    result.update(base_meta)
    if not result.get("band_energy"):
        result["band_energy"] = band_energy
    return AcousticResponse(**result)
