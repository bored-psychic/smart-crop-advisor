"""Acoustic pest detection router."""

import base64
import importlib
import io
import json
import logging
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

logger = logging.getLogger(__name__)

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

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    img_b64 = base64.standard_b64encode(spec_bytes).decode()
    dsp_block = json.dumps(dsp_features, indent=2)

    system_text = (
        "You are an expert bioacoustics analyst for crop pest detection. "
        "You analyze field-audio spectrograms and supporting DSP features to "
        "identify whatever sound is actually present — a pest, a disease "
        "signature, ambient noise, mechanical noise, wind, birds, or silence.\n\n"
        "REFERENCE SIGNATURES (well-studied in this tool — copy these exact "
        "labels when the recording clearly matches one):\n"
        "- Healthy Plant: flat noise floor, low energy across all bands\n"
        "- Aphid Colony: clustered mid-frequency bursts 200-400 Hz\n"
        "- Whitefly Infestation: wing-beat harmonic series 400-700 Hz\n"
        "- Locust Activity: high-amplitude low-frequency pulses 50-200 Hz\n"
        "- Stem Borer: rhythmic low-frequency gnawing 50-150 Hz\n"
        "- Early Fungal Infection: high-frequency crackling 800-1200 Hz\n"
        "- Spider Mite: ultra-high-frequency scratching 1200-4000 Hz\n"
        "- Thrips Infestation: rapid mid-frequency staccato 350-500 Hz\n\n"
        "OPEN VOCABULARY: identify whatever you actually hear. If the "
        "signature clearly matches one of the labels above, copy that exact "
        "label. Otherwise return the most specific accurate name (species or "
        "group, e.g. 'Mealybug', 'Leafhopper', 'Fall Armyworm', 'Mechanical "
        "/ Pump Noise', 'Wind', 'Bird Vocalization', 'Silence / Ambient'). "
        "Do NOT force an answer into the listed labels if it doesn't fit.\n\n"
        "When the recording is NOT a pest signal (wind, mechanical, biological-"
        "but-non-pest like birds, ambient silence), set is_pest=false and use "
        "the action field to tell the farmer what was heard and how to record "
        "a cleaner sample.\n\n"
        "CALIBRATION RULES:\n"
        "1. Spectrogram analysis is exploratory — be conservative.\n"
        "2. Confidence MUST be ≤ 70 unless the signature is textbook and "
        "unambiguous.\n"
        "3. For weak/partial matches, use confidence 30-55.\n"
        "4. Use the supplied crop type to favor ecologically plausible pests.\n"
        "5. The DSP feature block (band energies, spectral centroid, ZCR) is "
        "more reliable than the spectrogram image — anchor your call to the "
        "numbers when they conflict.\n\n"
        "Respond ONLY with valid JSON (NO markdown fences, NO commentary):\n"
        '{"pest":"name (canonical reference label when matched)",'
        '"is_pest":true|false,'
        '"severity":"high|medium|low",'
        '"freq_range":"e.g. 50-150 Hz",'
        '"pattern":"what you see in spectrogram + DSP",'
        '"energy_level":"Very High|High|Moderate|Low-moderate|Background",'
        '"confidence":<int 0-100>,'
        '"action":"specific actionable advice for an Indian smallholder farmer",'
        '"icon":"single emoji (canonical icon when matched, else your choice)",'
        '"top3":[["Pest1",85],["Pest2",10],["Pest3",5]]}'
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
        "Listen to this short field audio recording from a farm. Describe "
        "ALL sounds you hear in objective, specific terms — temporal pattern "
        "(rhythmic / random / continuous / burst-like), frequency character "
        "(high-pitched / low rumble / mid-range), texture (clicking / buzzing "
        "/ crackling / scraping / rustling / humming), amplitude level (faint "
        "/ moderate / strong), and any other distinctive features. "
        "Do NOT name any pest, disease, or species — only describe what you "
        "actually hear. 3 to 5 sentences maximum."
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
        if desc:
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

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_text = (
        "You are an expert entomologist and bioacoustics specialist for "
        "Indian crop pest detection. A colleague (an AI audio listener) "
        "heard a raw field recording and described what they heard — "
        "without naming any pest. Using your entomological knowledge, "
        "identify the most likely cause of the sound.\n\n"
        "OPEN VOCABULARY: if the description clearly matches a well-studied "
        "category, copy the exact label ('Aphid Colony', 'Whitefly "
        "Infestation', 'Locust Activity', 'Stem Borer', 'Early Fungal "
        "Infection', 'Spider Mite', 'Thrips Infestation', 'Healthy Plant'). "
        "Otherwise return the most specific accurate name ('Mealybug', "
        "'Leafhopper', 'Fall Armyworm', 'Wind', 'Bird Vocalization', "
        "'Mechanical / Pump Noise', 'Silence / Ambient', etc.). Do NOT force "
        "an answer into the listed labels if it doesn't fit.\n\n"
        "When the recording is NOT a pest signal (wind, mechanical, "
        "biological-but-non-pest like birds, ambient silence), set "
        "is_pest=false and use the action field to advise the farmer how to "
        "record a cleaner sample.\n\n"
        "CALIBRATION RULES:\n"
        "1. Acoustic identification from a sound description is exploratory "
        "— be conservative.\n"
        "2. Confidence MUST be ≤ 70 unless the description is textbook and "
        "unambiguous.\n"
        "3. For weak/partial matches, use confidence 30-55.\n"
        "4. Use the supplied crop type to favor ecologically plausible "
        "pests.\n\n"
        "Respond ONLY with valid JSON (NO markdown fences, NO commentary):\n"
        '{"pest":"name (canonical reference label when matched)",'
        '"is_pest":true|false,'
        '"severity":"high|medium|low",'
        '"freq_range":"your best estimate, e.g. 50-150 Hz",'
        '"pattern":"brief description of the temporal/spectral pattern",'
        '"energy_level":"Very High|High|Moderate|Low-moderate|Background",'
        '"confidence":<int 0-100>,'
        '"action":"specific actionable advice for an Indian smallholder farmer",'
        '"icon":"single emoji",'
        '"top3":[["Pest1",85],["Pest2",10],["Pest3",5]]}'
    )

    user_text = (
        f"Crop: {crop_type}.\n\n"
        f"Audio description from {gemini_model} (Gemini's native-audio "
        f"listener):\n\"\"\"\n{sound_description}\n\"\"\"\n\n"
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
        '{"pest":"name","is_pest":true|false,"severity":"high|medium|low",'
        '"freq_range":"e.g. 50-150 Hz",'
        '"pattern":"brief temporal/spectral pattern",'
        '"energy_level":"Very High|High|Moderate|Low-moderate|Background",'
        '"confidence":<int 0-100>,'
        '"action":"specific advice for an Indian smallholder farmer",'
        '"icon":"single emoji",'
        '"top3":[["Pest1",85],["Pest2",10],["Pest3",5]]}'
    )
    prompt = (
        "You are an expert entomologist for Indian crop pest detection. "
        f"Crop: {crop_type}.\n\n"
        f"Audio description from a separate listener:\n\"\"\"\n"
        f"{sound_description}\n\"\"\"\n\n"
        "Identify the most likely cause of the sound. Use canonical labels "
        "where they fit ('Aphid Colony', 'Whitefly Infestation', 'Locust "
        "Activity', 'Stem Borer', 'Early Fungal Infection', 'Spider Mite', "
        "'Thrips Infestation', 'Healthy Plant'); otherwise use the most "
        "specific accurate name. Set is_pest=false for non-pest signals.\n\n"
        "Calibration: confidence MUST be ≤ 70 unless textbook-unambiguous; "
        "use 30-55 for weak/partial matches.\n\n"
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
      1. exact         "Aphid Colony"   → "Aphid Colony"
      2. case fold     "aphid colony"   → "Aphid Colony"
      3. plural fold   "Spider Mites"   → "Spider Mite"
      4. unambiguous substring  "Aphids" → "Aphid Colony"
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
        "is_pest": is_pest,
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
    }

    # AI dispatch. The two-step Gemini → Claude pipeline is preferred when
    # GEMINI_API_KEY is set: Gemini hears the audio (no pest names allowed in
    # the prompt) and Claude reasons over Gemini's plain-language description.
    # When only ANTHROPIC_API_KEY is set, we fall back to the legacy
    # spectrogram-vision path. When neither key is set, _claude_acoustic
    # returns the no_api_key sentinel which routes into the synthetic
    # Random-Forest offline demo.
    settings_ref = get_settings()
    ai_result: Optional[dict] = None
    ai_method = "uncertain"

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
            # Gemini describe step failed but Claude vision is available —
            # graceful fallback to the legacy spectrogram path.
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
        # No Gemini key: preserve the original claude_vision-or-RFB behavior.
        # _claude_acoustic returns the no_api_key sentinel when
        # ANTHROPIC_API_KEY is also unset, which routes us into the
        # offline-demo branch below.
        ai_result = await _claude_acoustic(
            spec_bytes, normalized_crop, dsp_features_for_claude
        )
        ai_method = "claude_vision"

    ai_pred, ai_reject_reason = _coerce_claude_prediction(ai_result)

    if ai_pred is not None:
        result = ai_pred
        result["ml_used"] = False
        result["analysis_method"] = ai_method
        result["cv_accuracy"] = None
        result["cv_label"] = None
        if isinstance(ai_result, dict):
            result["claude_model_used"] = ai_result.get("_model_used")
    elif isinstance(ai_result, dict) and ai_result.get("stage") == "no_api_key":
        # Offline-demo path — synthetic RF, badged distinctly in the UI. No
        # extra quality_warning entry: analysis_method='random_forest_offline_demo'
        # is the canonical signal.
        acoustic_bundle = request.app.state.acoustic_model
        if acoustic_bundle is None:
            raise HTTPException(status_code=503, detail="Acoustic model unavailable")
        result = acoustic_bundle.predict(features, crop_type=normalized_crop)
        result["analysis_method"] = "random_forest_offline_demo"
        result["is_pest"] = result.get("pest") != "Healthy Plant"
    else:
        # AI tried but failed: analysis_method='uncertain' surfaces the real
        # failure stage to the UI rather than dressing up a synthetic guess.
        result = _build_uncertain_result(ai_result, ai_reject_reason)

    result.update(base_meta)
    if not result.get("band_energy"):
        result["band_energy"] = band_energy
    return AcousticResponse(**result)


def _build_uncertain_result(
    claude_result: Optional[dict],
    reject_reason: Optional[str],
) -> dict:
    """Construct the schema dict for the new analysis_method='uncertain' branch.

    Used when ANTHROPIC_API_KEY is set but Claude either errored or produced
    output the validator could not accept. The diagnostic fields let the UI
    surface the real failure (api_call/json_parse/validation/etc.) instead
    of dressing up a synthetic RF guess.
    """
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
