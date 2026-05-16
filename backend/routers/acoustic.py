"""Acoustic pest detection router."""

import base64
import datetime as dt
import hashlib
import importlib
import io
import json
import logging
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Optional

import numpy as np
import scipy.io.wavfile as wav
from PIL import Image
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File, Form
from backend.schemas.acoustic import AcousticResponse
from backend.ml.acoustic_model import _features_from_pcm, _normalize_crop_type
from backend.auth import require_api_key
from backend.config import get_settings
from backend.core.constants import PEST_META

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/acoustic", tags=["Acoustic Pest Detection"])

# Active-learning feedback storage. Clips are saved as 16-bit WAV; feedback
# entries are written as JSONL. The retrain script picks these up.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FEEDBACK_CLIPS_DIR = _REPO_ROOT / "data" / "feedback_clips"
FEEDBACK_QUEUE_FILE = _REPO_ROOT / "data" / "feedback_queue" / "feedback.jsonl"
AUDIO_SAMPLES_DIR = _REPO_ROOT / "data" / "audio_samples"

# Save clips for farmer review when top-1 confidence is below this value (%).
FEEDBACK_CONFIDENCE_THRESHOLD = 60

PEST_ICONS = {name: meta['icon'] for name, meta in PEST_META.items()}

MAX_ANALYSIS_SECONDS = 20
MIN_ANALYSIS_SECONDS = 1.5
MIN_RMS = 1e-4

# Audio-hash response cache. The full pipeline (resample + YAMNet + maybe two
# API round-trips) is expensive and deterministic for a fixed input; users
# retry the same upload often enough that an LRU keyed on sha256(audio_bytes,
# crop_type) saves real money and latency. Bounded so it can't grow without
# limit on a long-running process.
_RESPONSE_CACHE: "OrderedDict[str, dict]" = OrderedDict()
_RESPONSE_CACHE_MAX = 64


def _cache_key(audio_bytes: bytes, crop_type: str) -> str:
    h = hashlib.sha256()
    h.update(audio_bytes)
    h.update(b"|")
    h.update((crop_type or "").encode("utf-8"))
    return h.hexdigest()


def _cache_get(key: str) -> Optional[dict]:
    if key in _RESPONSE_CACHE:
        _RESPONSE_CACHE.move_to_end(key)
        return _RESPONSE_CACHE[key]
    return None


def _cache_put(key: str, value: dict) -> None:
    _RESPONSE_CACHE[key] = value
    _RESPONSE_CACHE.move_to_end(key)
    while len(_RESPONSE_CACHE) > _RESPONSE_CACHE_MAX:
        _RESPONSE_CACHE.popitem(last=False)


# ── Feedback / active-learning helpers ────────────────────────────────────────

def _save_feedback_clip(pcm: np.ndarray, rate: int) -> str:
    """Write decoded PCM to feedback_clips/ and return the clip UUID."""
    FEEDBACK_CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    clip_id = str(uuid.uuid4())
    out = FEEDBACK_CLIPS_DIR / f"{clip_id}.wav"
    int16 = np.clip(pcm * 32767.0, -32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    wav.write(buf, rate, int16)
    out.write_bytes(buf.getvalue())
    return clip_id


class _FeedbackBody(BaseModel):
    clip_id: str
    corrected_label: str
    predicted_label: str = ""
    confidence: int = 0
    crop_type: str = "Unknown"
    analysis_method: str = "panns"


@router.post("/feedback")
async def submit_feedback(body: _FeedbackBody, _: str = Depends(require_api_key)):
    """Record a farmer label correction and move the clip to the training queue.

    Called by the frontend when a user submits the "Help improve the AI" widget.
    The clip UUID must match a file already saved in FEEDBACK_CLIPS_DIR (created
    at analysis time when confidence was below FEEDBACK_CONFIDENCE_THRESHOLD).
    If the corrected_label is "skip" the clip is left in place but not queued.
    """
    label = (body.corrected_label or "").strip()
    if not label or label.lower() == "skip":
        return {"status": "skipped"}

    clip_src = FEEDBACK_CLIPS_DIR / f"{body.clip_id}.wav"
    if not clip_src.exists():
        raise HTTPException(status_code=404, detail="clip_id not found")

    # Copy clip to the matching training-data folder so the next retrain run
    # picks it up automatically via collect_dataset().
    dest_dir = AUDIO_SAMPLES_DIR / label.replace("/", "_").replace(" ", "_")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"feedback_{body.clip_id}.wav"
    dest.write_bytes(clip_src.read_bytes())

    # Append to JSONL queue for audit / statistics.
    FEEDBACK_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": dt.datetime.utcnow().isoformat() + "Z",
        "clip_id": body.clip_id,
        "predicted_label": body.predicted_label,
        "corrected_label": label,
        "confidence": body.confidence,
        "crop_type": body.crop_type,
        "analysis_method": body.analysis_method,
    }
    with FEEDBACK_QUEUE_FILE.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")

    logger.info(
        "feedback: clip %s labelled as '%s' (was '%s' @ %d%%)",
        body.clip_id, label, body.predicted_label, body.confidence,
    )
    return {"status": "ok", "dest": str(dest)}


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

    # Weather noise heuristic: high spectral flatness (wind/rain ≈ white noise),
    # low onset density (no discrete insect events), and low-band energy
    # dominance (wind is sub-500 Hz heavy) all point toward non-biological noise.
    try:
        seg_f = seg.astype(np.float32, copy=False)
        flatness = float(np.mean(librosa.feature.spectral_flatness(y=seg_f)))
        fft_mag = np.abs(np.fft.rfft(seg_f))
        freqs = np.fft.rfftfreq(len(seg_f), 1.0 / rate)
        low_energy = fft_mag[freqs < 500].mean() if (freqs < 500).any() else 0.0
        total_energy = fft_mag.mean() or 1e-9
        low_ratio = float(low_energy / total_energy)
        onset_score = max(0.0, 1.0 - ((density or 0.0) / 3.0))
        weather_noise_score = round(
            0.5 * min(flatness * 4, 1.0) +
            0.3 * onset_score +
            0.2 * min(low_ratio, 1.0),
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


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` fences from Claude's output."""
    s = text.strip()
    if not s.startswith("```"):
        return s
    s = s.lstrip("`")
    if s.lower().startswith("json"):
        s = s[4:]
    s = s.lstrip()
    if s.endswith("```"):
        s = s[:-3].rstrip()
    return s.strip()


async def _claude_acoustic(
    spec_bytes: bytes,
    crop_type: str,
    dsp_features: dict,
) -> dict:
    """Call Claude vision on the spectrogram + a DSP feature text block.

    Returns either a parsed JSON dict (success, with `_model_used` annotation)
    or a structured failure dict: {"failed": True, "stage": ..., "detail": ...,
    "attempts": [...]}. The "no_api_key" stage is special — the endpoint
    treats it as the offline-demo signal rather than a real failure.
    """
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        return {"failed": True, "stage": "no_api_key",
                "detail": "ANTHROPIC_API_KEY not set"}

    try:
        from anthropic import AsyncAnthropic
    except Exception as exc:
        logger.warning("acoustic: anthropic SDK import failed: %s", exc)
        return {"failed": True, "stage": "sdk_import",
                "detail": str(exc)[:200]}

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=15.0)
    img_b64 = base64.standard_b64encode(spec_bytes).decode()
    dsp_block = json.dumps(dsp_features, indent=2)

    system_text = (
        "You are an expert bioacoustics analyst for Indian crop fields. You "
        "analyze field-audio spectrograms and DSP features to identify "
        "audible insect activity — pests, pollinators, health vectors, "
        "ambient indicators, or genuine silence. The phone mic is held "
        "15-30 cm from the crop.\n\n"
        "ACOUSTIC VOCABULARY (use these exact labels when the recording "
        "matches; the role drives how the farmer is advised):\n"
        "TIER 1 — reliably audible from a phone mic:\n"
        "- Helicoverpa armigera (pest, 1-4 kHz broadband): larval chewing on "
        "fruit/pods + frass fall. Cotton/Tomato/Chickpea/Pigeon Pea.\n"
        "- Fall Armyworm (pest, 1-4 kHz broadband): larval chewing in maize "
        "whorl + frass. Maize.\n"
        "- Locust Activity (pest, 50-200 Hz, very high amplitude): wingbeat "
        "+ mass flight hum. Rare but unmistakable.\n"
        "- Grasshopper Activity (pest, 3-10 kHz stridulation): daytime "
        "defoliation; high India relevance in dry season.\n"
        "- Cicada Activity (pest in orchards, ambient elsewhere, 4-10 kHz "
        "sustained buzz): oviposition damage on mango/coffee twigs.\n"
        "- Cricket Ambient (ambient, 3-7 kHz chirp): nighttime insect "
        "pressure proxy and 'mic is working' anchor. NOT a pest.\n"
        "- Honey Bee Activity (pollinator, 200-300 Hz wingbeat): foraging "
        "swarm or nearby hives. POSITIVE signal — protect, not treat.\n"
        "TIER 2 — close-range only, lower confidence (set low_signal=true):\n"
        "- Rice Stem Borer (pest, 50-200 Hz faint): internal stem feeding.\n"
        "- Banana Pseudostem Weevil (pest, 50-500 Hz faint, intermittent): "
        "boring sounds in pseudostem.\n"
        "- Mosquito Activity (vector, 400-700 Hz wingbeat): NOT a crop "
        "pest — health advisory only (dengue/malaria context).\n"
        "TIER 0 — explicit silence:\n"
        "- Quiet / No Audible Activity (ambient): noise floor only, no "
        "insect activity. Return this confidently when nothing audible is "
        "present — better than guessing a pest.\n\n"
        "ROLES drive farmer guidance — be careful:\n"
        "- pest      → treatment advice\n"
        "- pollinator → encourage / protect, NEVER recommend insecticide\n"
        "- vector    → health advisory (drain standing water, mosquito net)\n"
        "- ambient   → no treatment, just an environment indicator\n\n"
        "OPEN VOCABULARY: if the recording clearly matches a label above, "
        "use it exactly. If it's some other identifiable sound (Mealybug, "
        "Leafhopper, Mechanical / Pump Noise, Wind, Bird Vocalization), "
        "return that name with is_pest=false where appropriate. Do NOT "
        "force an answer into the labels above if it doesn't fit. Do NOT "
        "return aphid, whitefly, spider mite, thrips, or fungal infection "
        "from this tool — those are silent at phone-mic range and belong "
        "to the visual-photo pipeline.\n\n"
        "CALIBRATION RULES:\n"
        "1. Spectrogram analysis is exploratory — be conservative.\n"
        "2. Confidence ≤ 70 unless the signature is textbook and "
        "unambiguous.\n"
        "3. Tier 2 entries cap at confidence 60 and MUST set "
        "low_signal=true with action text starting 'Verify visually before "
        "treating'.\n"
        "4. For weak/partial matches, use confidence 30-55.\n"
        "5. For genuine silence, return Quiet / No Audible Activity with "
        "confidence 70-90 — high confidence is honest here.\n"
        "6. Use the supplied crop type to favor ecologically plausible "
        "species.\n"
        "7. The DSP feature block (band energies, spectral centroid, ZCR) "
        "is more reliable than the spectrogram image — anchor your call to "
        "the numbers when they conflict.\n\n"
        "Respond ONLY with valid JSON (NO markdown fences, NO commentary):\n"
        '{"pest":"name (canonical label when matched)",'
        '"role":"pest|pollinator|vector|ambient",'
        '"is_pest":true|false,'
        '"low_signal":true|false,'
        '"severity":"high|medium|low",'
        '"freq_range":"e.g. 50-150 Hz",'
        '"pattern":"what you see in spectrogram + DSP",'
        '"energy_level":"Very High|High|Moderate|Low-moderate|Background",'
        '"confidence":<int 0-100>,'
        '"action":"specific advice matched to the role (treat / protect / '
        'health / no action)",'
        '"icon":"single emoji",'
        '"top3":[["Label1",85],["Label2",10],["Label3",5]]}'
    )

    user_text = (
        f"Crop: {crop_type}.\n\n"
        f"DSP features extracted from the recording:\n```json\n{dsp_block}\n```\n\n"
        "Analyze the spectrogram (image) together with the DSP features. "
        "Respond with the JSON object only."
    )

    model_candidates = ["claude-opus-4-7", "claude-sonnet-4-6"]
    attempts: list[dict] = []

    for model_name in model_candidates:
        text = ""
        try:
            resp = await client.messages.create(
                model=model_name,
                max_tokens=700,
                system=[{
                    "type": "text",
                    "text": system_text,
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
                        {"type": "text", "text": user_text},
                    ],
                }],
            )
        except Exception as exc:
            detail = str(exc)[:200]
            logger.warning("acoustic: %s api_call failed: %s", model_name, detail)
            attempts.append({"model": model_name, "stage": "api_call", "detail": detail})
            continue

        try:
            text = resp.content[0].text.strip()
            text = _strip_markdown_fences(text)
            parsed = json.loads(text)
        except Exception as exc:
            detail = str(exc)[:200]
            logger.warning("acoustic: %s json_parse failed: %s | raw=%r",
                           model_name, detail, text[:300])
            attempts.append({"model": model_name, "stage": "json_parse",
                             "detail": detail, "raw": text[:300]})
            continue

        if not isinstance(parsed, dict):
            attempts.append({"model": model_name, "stage": "json_parse",
                             "detail": f"top-level not a dict ({type(parsed).__name__})"})
            continue

        parsed["_model_used"] = model_name
        return parsed

    return {
        "failed": True,
        "stage": "all_models_failed",
        "detail": f"tried {len(attempts)} model(s)",
        "attempts": attempts,
    }


async def _gemini_describe_audio(
    wav_bytes: bytes,
) -> tuple[Optional[str], Optional[str]]:
    """Listen-and-describe step (the unbiased "hearing layer").

    Gemini's only job here is to translate raw audio into a plain-language
    description — temporal pattern, frequency character, texture, amplitude.
    The prompt deliberately forbids naming any pest so Claude is not handed
    a pre-made answer to confirm.

    Returns (description, model_name) on success or (None, error_reason) on
    failure. Model fallback order:
      1. gemini-2.5-flash       — primary, native audio understanding
      2. gemini-2.5-flash-lite  — cheaper 2.5-series fallback
      3. gemini-2.0-flash       — last-resort 2.0-series fallback
    """
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        return None, "no_api_key"
    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        return None, f"sdk_import:{str(exc)[:120]}"

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as exc:
        return None, f"client_init:{str(exc)[:120]}"

    audio_part = types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav")
    prompt = (
        "Listen to this farm field audio recording and answer each question "
        "on its own line in the exact format shown. Do NOT name any pest, "
        "disease, or species.\n\n"
        "PATTERN: <rhythmic|irregular-bursts|continuous|random|silent>\n"
        "TEXTURE: <clicking|scraping-rasping|buzzing|humming|rushing-wind|"
        "tonal-melodic|mixed-clicking-scraping>\n"
        "FREQUENCY: <very-high-4kHz+|high-2to4kHz|mid-500Hz-2kHz|mid-low-200to500Hz|very-low-under-200Hz>\n"
        "AMPLITUDE: <strong|moderate|faint>\n"
        "AMPLITUDE_VARIATION: <organic-rises-falls|steady-constant|pulsing-regular>\n"
        "BURST_DURATION: <under-0.5s|0.5-2s|2-5s|continuous>\n"
        "SOUND_ORIGIN: <biological-insect|biological-bird|mechanical|wind|unknown>\n"
        "NOTES: <one sentence of any other distinctive detail, or 'none'>"
    )

    for model_name in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]:
        try:
            resp = await client.aio.models.generate_content(
                model=model_name,
                contents=[audio_part, prompt],
                config=types.GenerateContentConfig(max_output_tokens=300),
            )
        except Exception as exc:
            logger.warning("acoustic: gemini %s describe failed: %s",
                           model_name, str(exc)[:200])
            continue
        desc = (getattr(resp, "text", None) or "").strip()
        # Require at least PATTERN and TEXTURE lines to be present
        if desc and "PATTERN:" in desc and "TEXTURE:" in desc:
            return desc, model_name
    return None, "all_gemini_models_failed"


async def _claude_from_description(
    sound_description: str,
    crop_type: str,
    gemini_model: str,
) -> dict:
    """Reasoning step: Claude maps Gemini's plain-language description to
    pest JSON using its entomology knowledge — no Hz hints, no DSP numbers,
    no spectrogram. Returns the same dict shape as `_claude_acoustic` so
    `_coerce_claude_prediction` works unchanged.
    """
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        return {"failed": True, "stage": "no_api_key",
                "detail": "ANTHROPIC_API_KEY not set"}
    try:
        from anthropic import AsyncAnthropic
    except Exception as exc:
        logger.warning("acoustic: anthropic SDK import failed: %s", exc)
        return {"failed": True, "stage": "sdk_import",
                "detail": str(exc)[:200]}

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=15.0)

    system_text = (
        "You are an expert entomologist and bioacoustics specialist for "
        "Indian crop fields. A colleague (an AI audio listener) heard a "
        "raw field recording and described what they heard — without "
        "naming any species. Using your entomological knowledge, identify "
        "the most likely source of the sound.\n\n"
        "ACOUSTIC VOCABULARY (use exact labels; the role drives advice):\n"
        "TIER 1 — phone-mic detectable:\n"
        "• Helicoverpa armigera (pest, 1-4 kHz broadband): coarse chewing "
        "and frass fall on fruit/pods. Cotton, Tomato, Chickpea, Pigeon Pea.\n"
        "• Fall Armyworm (pest, 1-4 kHz broadband): same texture in maize "
        "whorl. Karnataka maize since 2018.\n"
        "• Locust Activity (pest, 50-200 Hz, very high amplitude): wingbeat "
        "+ mass flight hum. Rare but unmistakable. Often chattering or "
        "whirring with organic variation.\n"
        "• Grasshopper Activity (pest, 3-10 kHz stridulation): rasping, "
        "scraping daytime chorus from field margins.\n"
        "• Cicada Activity (pest in orchards / ambient elsewhere, 4-10 kHz "
        "sustained buzz): tonal, almost continuous; mango and coffee context.\n"
        "• Cricket Ambient (ambient, 3-7 kHz chirp): rhythmic nighttime "
        "stridulation. NOT a pest — useful 'mic is working' indicator.\n"
        "• Honey Bee Activity (pollinator, 200-300 Hz wingbeat): low warm "
        "hum from foraging bees / nearby hives. POSITIVE signal.\n"
        "TIER 2 — faint, requires close mic; mark low_signal=true:\n"
        "• Rice Stem Borer (pest, 50-200 Hz faint): intermittent gnawing/"
        "tapping deep inside a tiller; hollow drilling quality.\n"
        "• Banana Pseudostem Weevil (pest, 50-500 Hz faint, intermittent): "
        "boring/scraping inside the pseudostem.\n"
        "• Mosquito Activity (vector — health advisory, NOT crop pest, "
        "400-700 Hz): high-pitched whine of female wingbeat at close range.\n"
        "TIER 0 — explicit silence:\n"
        "• Quiet / No Audible Activity (ambient): the description shows no "
        "biological signal — wind only, true silence, or just noise floor. "
        "Return this confidently rather than guessing a pest.\n\n"
        "DISAMBIGUATION RULES:\n"
        "- Clicking, scraping, chattering, rattling with irregular timing "
        "→ biological (insect stridulation), NOT mechanical.\n"
        "- Reserve 'Mechanical / Pump Noise' only for steady, constant, "
        "tonally flat hum.\n"
        "- Aphid / whitefly / spider mite / thrips / fungal infection are "
        "INAUDIBLE at phone-mic range — never return these labels here.\n"
        "- A bee hum (200-300 Hz, organic, sustained, warm) is a "
        "pollinator, not a pest. Frame it as such.\n"
        "- A mosquito whine (400-700 Hz at close range) is a health "
        "concern, not a crop pest. Action goes to standing-water hygiene "
        "and dengue/malaria watch.\n\n"
        "ROLES drive farmer guidance:\n"
        "- pest      → treatment advice\n"
        "- pollinator → encourage / protect, NEVER recommend insecticide\n"
        "- vector    → health advisory (drain standing water, net at night)\n"
        "- ambient   → no treatment, just an environment indicator\n\n"
        "OPEN VOCABULARY: if the description doesn't match the labels "
        "above, return the most specific accurate name (e.g. 'Mealybug', "
        "'Leafhopper', 'Wind', 'Bird Vocalization', 'Mechanical / Pump "
        "Noise') with is_pest=false where appropriate.\n\n"
        "CALIBRATION RULES:\n"
        "1. Be honest about uncertainty.\n"
        "2. Strong fingerprint match → confidence 70-85.\n"
        "3. Tier 2 entries cap at 60 and MUST set low_signal=true and "
        "action text starting 'Verify visually before treating'.\n"
        "4. Weak / ambiguous → confidence 30-55.\n"
        "5. Genuine silence → return Quiet / No Audible Activity at "
        "confidence 70-90; honest silence is high-value, not a failure.\n"
        "6. Use the supplied crop type to favor ecologically plausible "
        "species.\n\n"
        "Respond ONLY with valid JSON (NO markdown fences, NO commentary):\n"
        '{"pest":"name (canonical label when matched)",'
        '"role":"pest|pollinator|vector|ambient",'
        '"is_pest":true|false,'
        '"low_signal":true|false,'
        '"severity":"high|medium|low",'
        '"freq_range":"your best estimate, e.g. 50-150 Hz",'
        '"pattern":"brief temporal/spectral pattern",'
        '"energy_level":"Very High|High|Moderate|Low-moderate|Background",'
        '"confidence":<int 0-100>,'
        '"action":"specific advice matched to the role",'
        '"icon":"single emoji",'
        '"top3":[["Label1",85],["Label2",10],["Label3",5]]}'
    )

    user_text = (
        f"Crop: {crop_type}.\n\n"
        f"Structured acoustic features extracted by {gemini_model} "
        f"(Gemini native-audio listener — pest/species names withheld):\n"
        f"\"\"\"\n{sound_description}\n\"\"\"\n\n"
        "Identify the pest or sound source from this description alone. "
        "Return the JSON object only."
    )

    model_candidates = ["claude-opus-4-7", "claude-sonnet-4-6"]
    attempts: list[dict] = []

    for model_name in model_candidates:
        text = ""
        try:
            resp = await client.messages.create(
                model=model_name,
                max_tokens=700,
                system=[{
                    "type": "text",
                    "text": system_text,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": user_text}],
            )
        except Exception as exc:
            detail = str(exc)[:200]
            logger.warning("acoustic: %s claude_from_desc api_call failed: %s",
                           model_name, detail)
            attempts.append({"model": model_name, "stage": "api_call",
                             "detail": detail})
            continue

        try:
            text = resp.content[0].text.strip()
            text = _strip_markdown_fences(text)
            parsed = json.loads(text)
        except Exception as exc:
            detail = str(exc)[:200]
            logger.warning("acoustic: %s claude_from_desc json_parse failed: %s | raw=%r",
                           model_name, detail, text[:300])
            attempts.append({"model": model_name, "stage": "json_parse",
                             "detail": detail, "raw": text[:300]})
            continue

        if not isinstance(parsed, dict):
            attempts.append({"model": model_name, "stage": "json_parse",
                             "detail": f"top-level not a dict ({type(parsed).__name__})"})
            continue

        parsed["_model_used"] = f"gemini:{gemini_model}+claude:{model_name}"
        return parsed

    return {
        "failed": True,
        "stage": "all_models_failed",
        "detail": f"tried {len(attempts)} model(s)",
        "attempts": attempts,
    }


async def _gemini_classify_direct(
    sound_description: str,
    crop_type: str,
    gemini_model: str,
) -> dict:
    """Gemini-only fallback: when ANTHROPIC_API_KEY is unset, ask Gemini to
    map its own description to the pest JSON. Same schema as
    `_claude_from_description`, so `_coerce_claude_prediction` works
    unchanged. Uses response_mime_type='application/json' so Gemini emits
    structured JSON natively.
    """
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        return {"failed": True, "stage": "no_api_key",
                "detail": "GEMINI_API_KEY not set"}
    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        return {"failed": True, "stage": "sdk_import", "detail": str(exc)[:200]}

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as exc:
        return {"failed": True, "stage": "client_init", "detail": str(exc)[:200]}

    schema_block = (
        '{"pest":"name",'
        '"role":"pest|pollinator|vector|ambient",'
        '"is_pest":true|false,'
        '"low_signal":true|false,'
        '"severity":"high|medium|low",'
        '"freq_range":"e.g. 50-150 Hz",'
        '"pattern":"brief temporal/spectral pattern",'
        '"energy_level":"Very High|High|Moderate|Low-moderate|Background",'
        '"confidence":<int 0-100>,'
        '"action":"specific advice matched to the role",'
        '"icon":"single emoji",'
        '"top3":[["Label1",85],["Label2",10],["Label3",5]]}'
    )
    prompt = (
        "You are an expert entomologist for Indian crop fields. "
        f"Crop: {crop_type}.\n\n"
        f"Audio description from a separate listener:\n\"\"\"\n"
        f"{sound_description}\n\"\"\"\n\n"
        "Identify the most likely source of the sound. Use canonical labels "
        "where they fit:\n"
        "TIER 1 (phone-mic audible): 'Helicoverpa armigera', 'Fall Armyworm', "
        "'Locust Activity', 'Grasshopper Activity', 'Cicada Activity', "
        "'Cricket Ambient', 'Honey Bee Activity'.\n"
        "TIER 2 (faint, set low_signal=true): 'Rice Stem Borer', "
        "'Banana Pseudostem Weevil', 'Mosquito Activity'.\n"
        "TIER 0 (silence): 'Quiet / No Audible Activity'.\n\n"
        "Roles: pest → treatment; pollinator → protect (no insecticide); "
        "vector → health advisory; ambient → no action. Bees are pollinators, "
        "mosquitoes are health vectors, crickets are ambient — frame them "
        "accordingly. Do NOT return aphid, whitefly, spider mite, thrips, or "
        "fungal infection here — those are silent at phone-mic range and "
        "belong to the visual-photo pipeline.\n\n"
        "If the description doesn't match a label above, return the most "
        "specific accurate name (e.g. 'Mealybug', 'Wind', 'Bird "
        "Vocalization', 'Mechanical / Pump Noise') with is_pest=false where "
        "appropriate.\n\n"
        "Calibration: confidence ≤ 70 unless textbook-unambiguous; Tier 2 "
        "caps at 60; for genuine silence return Quiet / No Audible Activity "
        "at confidence 70-90; weak/partial 30-55.\n\n"
        f"Respond ONLY with valid JSON matching this schema:\n{schema_block}"
    )

    seen: set[str] = set()
    candidates: list[str] = []
    for m in [gemini_model, "gemini-2.5-flash", "gemini-2.0-flash"]:
        if m and m not in seen:
            candidates.append(m)
            seen.add(m)

    attempts: list[dict] = []
    for model_name in candidates:
        try:
            resp = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=600,
                    response_mime_type="application/json",
                ),
            )
        except Exception as exc:
            detail = str(exc)[:200]
            logger.warning("acoustic: gemini_classify %s api_call failed: %s",
                           model_name, detail)
            attempts.append({"model": model_name, "stage": "api_call",
                             "detail": detail})
            continue

        text = (getattr(resp, "text", None) or "").strip()
        text = _strip_markdown_fences(text)
        try:
            parsed = json.loads(text)
        except Exception as exc:
            detail = str(exc)[:200]
            logger.warning("acoustic: gemini_classify %s json_parse failed: %s | raw=%r",
                           model_name, detail, text[:300])
            attempts.append({"model": model_name, "stage": "json_parse",
                             "detail": detail, "raw": text[:300]})
            continue

        if not isinstance(parsed, dict):
            attempts.append({"model": model_name, "stage": "json_parse",
                             "detail": f"top-level not a dict ({type(parsed).__name__})"})
            continue

        parsed["_model_used"] = f"gemini:{model_name}"
        return parsed

    return {
        "failed": True,
        "stage": "all_models_failed",
        "detail": f"tried {len(attempts)} model(s)",
        "attempts": attempts,
    }


_VALID_PESTS = list(PEST_META.keys())
_VALID_PESTS_LOWER = {name.lower(): name for name in _VALID_PESTS}

# Sanity floor: drops empty hallucinations only. Claude's own calibration
# rules cap weak matches at 30-55, so any value above this is treated as a
# real call rather than second-guessed here.
_CLAUDE_MIN_CONFIDENCE = 5


def _normalize_pest_name(raw) -> Optional[str]:
    """Canonicalize a raw pest name to a PEST_META key when it matches one.

    Returns the canonical name on hit, or None when the name is genuinely
    free-form. None is NOT a rejection — the caller accepts the original
    label as-is.

    Matching layers (case-insensitive, increasingly tolerant):
      1. exact         "Locust Activity" → "Locust Activity"
      2. case fold     "locust activity" → "Locust Activity"
      3. plural fold   "Helicoverpas"    → "Helicoverpa armigera"
      4. unambiguous substring  "Helicoverpa" → "Helicoverpa armigera"
    """
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None

    if s in _VALID_PESTS:
        return s

    lower = s.lower()
    if lower in _VALID_PESTS_LOWER:
        return _VALID_PESTS_LOWER[lower]

    if lower.endswith("s"):
        singular = lower[:-1]
        if singular in _VALID_PESTS_LOWER:
            return _VALID_PESTS_LOWER[singular]

    needles = [lower]
    if lower.endswith("s"):
        needles.append(lower[:-1])

    for needle in needles:
        if len(needle) < 4:
            continue  # avoid spurious matches on tiny tokens
        hits = [canon for canon_lower, canon in _VALID_PESTS_LOWER.items()
                if needle in canon_lower]
        if len(hits) == 1:
            return hits[0]

    return None


def _coerce_claude_prediction(raw) -> tuple[Optional[dict], Optional[str]]:
    """Validate Claude's parsed JSON.

    Returns:
      (coerced_dict, None) on success
      (None, reason_str)   on rejection — reason names the failed check so the
                           UI can show a real diagnostic instead of a generic
                           'analysis unavailable' message.

    The validator accepts free-form pest names (Mealybug, Leafhopper, Fall
    Armyworm, ...) — it's a shape check, not a name filter. Canonical names
    still get PEST_META metadata defaults; unknown names fall back to
    Claude's self-described severity/freq_range/pattern/etc.
    """
    if not isinstance(raw, dict):
        return None, "not_a_dict"

    if raw.get("failed"):
        stage = str(raw.get("stage", "unknown"))
        detail = str(raw.get("detail", ""))
        return None, f"{stage}: {detail}" if detail else stage

    pest_raw = raw.get("pest")
    if not isinstance(pest_raw, str) or not pest_raw.strip():
        return None, "missing_required_field: pest"
    pest = pest_raw.strip()

    try:
        confidence = int(round(float(raw.get("confidence", 0))))
    except (TypeError, ValueError):
        return None, "invalid_field: confidence"
    if confidence < _CLAUDE_MIN_CONFIDENCE:
        return None, f"confidence_below_floor: {confidence}"
    confidence = max(0, min(100, confidence))

    canonical = _normalize_pest_name(pest)
    if canonical is not None:
        meta = PEST_META[canonical]
        pest = canonical
        defaults = {
            "severity": meta["severity"],
            "freq_range": meta["freq_range"],
            "pattern": meta["pattern"],
            "energy_level": meta["energy_level"],
            "icon": meta["icon"],
            "action": meta["action"],
            "role": meta.get("role", "pest"),
            "low_signal": bool(meta.get("low_signal", False)),
        }
    else:
        defaults = {
            "severity": "medium",
            "freq_range": "—",
            "pattern": "—",
            "energy_level": "—",
            "icon": "🐛",
            "action": "Take a closer recording or cross-check with the photo "
                      "diagnosis tab before applying treatment.",
            "role": "pest",
            "low_signal": False,
        }

    severity = str(raw.get("severity") or defaults["severity"])
    freq_range = str(raw.get("freq_range") or defaults["freq_range"])
    pattern = str(raw.get("pattern") or defaults["pattern"])
    energy_level = str(raw.get("energy_level") or defaults["energy_level"])
    icon = str(raw.get("icon") or defaults["icon"])
    action_raw = raw.get("action")
    action = (str(action_raw).strip() if action_raw else "") or defaults["action"]

    is_pest_raw = raw.get("is_pest")
    is_pest = bool(is_pest_raw) if is_pest_raw is not None else True

    # Role: prefer canonical PEST_META, then AI-supplied (validated against
    # the four allowed values), else fall back to is_pest-driven default.
    role_raw = raw.get("role")
    valid_roles = {"pest", "pollinator", "vector", "ambient"}
    if canonical is not None:
        role = defaults["role"]
    elif isinstance(role_raw, str) and role_raw.strip().lower() in valid_roles:
        role = role_raw.strip().lower()
    else:
        role = "pest" if is_pest else "ambient"

    # low_signal: canonical wins; otherwise honor AI's flag for any name
    # mentioning Tier 2 species, else default False.
    if canonical is not None:
        low_signal = defaults["low_signal"]
    else:
        low_signal_raw = raw.get("low_signal")
        low_signal = bool(low_signal_raw) if low_signal_raw is not None else False

    raw_top3 = raw.get("top3") or []
    cleaned_top3: list[tuple[str, int]] = []
    if isinstance(raw_top3, list):
        for entry in raw_top3[:3]:
            try:
                name = str(entry[0]).strip()
                if not name:
                    continue
                canonical_n = _normalize_pest_name(name)
                if canonical_n:
                    name = canonical_n
                score = int(round(float(entry[1])))
            except (TypeError, ValueError, IndexError):
                continue
            cleaned_top3.append((name, max(0, min(100, score))))
    if not cleaned_top3:
        cleaned_top3 = [(pest, confidence)]

    coerced = {
        "pest": pest,
        "role": role,
        "is_pest": is_pest,
        "low_signal": low_signal,
        "severity": severity,
        "freq_range": freq_range,
        "pattern": pattern,
        "energy_level": energy_level,
        "confidence": confidence,
        "action": action,
        "icon": icon,
        "top3": cleaned_top3,
        "claude_advice": action or None,
    }
    return coerced, None


def _rejected(reason: str, warnings: list[str], duration: float, sr: int,
              decode: Optional[str]) -> AcousticResponse:
    return AcousticResponse(
        pest='Analysis Rejected',
        role='ambient',
        low_signal=False,
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

    cache_key = _cache_key(contents, normalized_crop)
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.info("acoustic: cache hit (sha=%s…)", cache_key[:12])
        return AcousticResponse(**cached)

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
        warnings.append("truncated_to_20s")
        seg = pcm[:rate * MAX_ANALYSIS_SECONDS]
    else:
        seg = pcm

    if rate < 8000:
        warnings.append(f"low_sample_rate_{rate}Hz")
    if rate > 48000:
        warnings.append(f"high_sample_rate_{rate}Hz")

    band_energy = _band_energies(seg, rate)
    snr_onset = _snr_and_onsets(seg, rate)

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

    # DSP feature block — Claude reasons over numbers more reliably than over
    # an unfamiliar spectrogram image, so we hand both to it together.
    dsp_features_for_claude = {
        "duration_seconds": round(duration, 2),
        "analyzed_seconds": round(min(duration, MAX_ANALYSIS_SECONDS), 2),
        "sample_rate_hz": rate,
        "rms": round(rms, 5),
        "band_energy": band_energy,
        "spectral_centroid_hz": round(features[4], 2),
        "zero_crossing_rate": round(features[5], 4),
        "peak_freq_bin": int(features[6]),
        "energy_variance": round(features[7], 5),
        "snr_db": snr_onset.get("snr_db"),
        "onset_density_per_sec": snr_onset.get("onset_density_per_sec"),
    }

    # Dispatch order:
    #   1. PANNs CNN14 (local, primary). Trained on real audio.
    #   2. Gemini→Claude API (fallback). Fires only when the local model is
    #      unavailable or raises — e.g., torch not installed, head file
    #      missing, checkpoint missing, runtime error.
    #   3. Claude vision on spectrogram (further fallback when only Anthropic
    #      key is set and Gemini describe step is unreachable).
    settings_ref = get_settings()
    ai_result: Optional[dict] = None
    ai_method = "uncertain"

    local_bundle = request.app.state.acoustic_model
    local_abstain_reason: Optional[str] = None
    if local_bundle is not None:
        try:
            ai_result = local_bundle.predict(
                seg, rate, crop_type=normalized_crop,
                weather_noise_score=snr_onset.get("weather_noise_score", 0.0),
            )
            # Bundle self-reports which backbone ran via _model_used; fall back
            # to "panns" since that's the only backbone wired today.
            ai_method = (ai_result or {}).get("_model_used", "panns")
        except Exception as exc:
            # Lazy imports — avoid pulling torch/joblib at module load.
            from backend.ml.panns_model import PANNsAbstain
            if isinstance(exc, PANNsAbstain):
                logger.info("acoustic: PANNs abstained: %s", exc)
                local_abstain_reason = str(exc)
            else:
                logger.warning("acoustic: PANNs predict failed: %s", exc)
            ai_result = None
            ai_method = "uncertain"

    if ai_result is None:
        # Local model unavailable — fall through to API pipeline.
        if settings_ref.GEMINI_API_KEY:
            wav_bytes = _encode_wav(seg, rate)
            sound_desc, gemini_info = await _gemini_describe_audio(wav_bytes)
            if sound_desc:
                ai_method = "gemini_audio"
                if settings_ref.ANTHROPIC_API_KEY:
                    ai_result = await _claude_from_description(
                        sound_desc, normalized_crop, gemini_info
                    )
                else:
                    ai_result = await _gemini_classify_direct(
                        sound_desc, normalized_crop, gemini_info
                    )
            elif settings_ref.ANTHROPIC_API_KEY and spec_bytes is not None:
                ai_result = await _claude_acoustic(
                    spec_bytes, normalized_crop, dsp_features_for_claude
                )
                ai_method = "claude_vision"
            else:
                ai_result = {
                    "failed": True,
                    "stage": f"gemini_describe:{gemini_info or 'unknown'}",
                    "detail": "Gemini audio listener could not produce a description.",
                }
        elif spec_bytes is not None:
            ai_result = await _claude_acoustic(
                spec_bytes, normalized_crop, dsp_features_for_claude
            )
            ai_method = "claude_vision"

    ai_pred, ai_reject_reason = _coerce_claude_prediction(ai_result)

    if ai_pred is not None:
        result = ai_pred
        result["ml_used"] = ai_method in ("panns", "yamnet")
        result["analysis_method"] = ai_method
        result["cv_accuracy"] = None
        result["cv_label"] = None
        if isinstance(ai_result, dict):
            result["claude_model_used"] = ai_result.get("_model_used")
            if ai_method in ("panns", "yamnet"):
                result["cv_accuracy"] = ai_result.get("_test_accuracy")
                result["cv_label"] = (
                    "PANNs CNN14 held-out test set" if ai_method == "panns"
                    else "YAMNet held-out test set"
                )
                result["all_class_confidence"] = ai_result.get("all_class_confidence")
                result["crop_prior_applied"] = bool(ai_result.get("_crop_prior_applied"))
                result["calibration_temperature"] = ai_result.get("_temperature")
                result["weather_noise_score"] = ai_result.get("weather_noise_score")
                result["yamnet_noise_score"] = ai_result.get("yamnet_noise_score")
    else:
        # All available pipelines failed. analysis_method='uncertain' surfaces
        # the real failure stage to the UI rather than dressing up a guess.
        result = _build_uncertain_result(
            ai_result, ai_reject_reason, local_abstain_reason
        )

    result.update(base_meta)
    if not result.get("band_energy"):
        result["band_energy"] = band_energy

    # Active-learning hook: save clip for feedback when confidence is low.
    # 'uncertain' always qualifies; local-model paths qualify below the
    # threshold (covers both PANNs and the YAMNet fallback if ever re-enabled).
    _method = result.get("analysis_method", "")
    _conf = int(result.get("confidence", 0))
    if _method == "uncertain" or (_method in ("panns", "yamnet") and _conf < FEEDBACK_CONFIDENCE_THRESHOLD):
        try:
            result["clip_id"] = _save_feedback_clip(seg, rate)
        except Exception as _exc:
            logger.warning("acoustic: could not save feedback clip: %s", _exc)

    _cache_put(cache_key, result)
    return AcousticResponse(**result)


def _build_uncertain_result(
    claude_result: Optional[dict],
    reject_reason: Optional[str],
    local_abstain_reason: Optional[str] = None,
) -> dict:
    """Construct the schema dict for the new analysis_method='uncertain' branch.

    Used when ANTHROPIC_API_KEY is set but Claude either errored or produced
    output the validator could not accept. The diagnostic fields let the UI
    surface the real failure (api_call/json_parse/validation/etc.) instead
    of dressing up a synthetic RF guess.
    """
    if local_abstain_reason and not claude_result:
        # Local model abstained AND no API path produced a result. Surface
        # the abstain reason instead of the empty 'unknown' fallback.
        stage = "local_abstain"
        detail = local_abstain_reason
    else:
        reason = (reject_reason or "unknown").strip()
        if ":" in reason:
            stage, _, detail = reason.partition(":")
            stage = stage.strip() or "unknown"
            detail = detail.strip()
        else:
            stage = reason
            detail = ""

    model_tried: Optional[str] = None
    if isinstance(claude_result, dict):
        attempts = claude_result.get("attempts") or []
        if attempts and isinstance(attempts[-1], dict):
            model_tried = attempts[-1].get("model")
        if not model_tried and claude_result.get("_model_used"):
            model_tried = claude_result.get("_model_used")

    return {
        "pest": "Uncertain",
        "role": "ambient",
        "low_signal": False,
        "is_pest": None,
        "severity": "low",
        "confidence": 0,
        "freq_range": "N/A",
        "pattern": "N/A",
        "energy_level": "N/A",
        "action": (
            "AI analysis could not produce a confident reading for this "
            "recording. Try recording closer to the crop in calmer "
            "conditions, or use Tab 2 (photo diagnosis) for a visual check."
        ),
        "icon": "❓",
        "top3": [],
        "ml_used": False,
        "analysis_method": "uncertain",
        "claude_failure_stage": stage,
        "claude_failure_detail": (detail[:200] if detail else None),
        "claude_model_used": model_tried,
        "cv_accuracy": None,
        "cv_label": None,
    }
