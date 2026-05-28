"""Acoustic analysis pipeline: load → normalize → DSP → ML → cache.

Orchestrates the full chain that the `/acoustic/analyze` route delegates to.
Pure orchestration — accepts raw audio bytes + crop type + the app's local
ML bundle and returns the result dict the route serializes.
"""

import logging
from typing import Callable, Optional

import numpy as np

from fastapi import HTTPException

from backend.config import get_settings
from backend.ml.acoustic_model import _features_from_pcm
from backend.schemas.acoustic import AcousticResponse
from backend.services.acoustic.cache import _cache_get, _cache_key, _cache_put
from backend.services.acoustic.dsp import (
    _band_energies,
    _decode_audio,
    _encode_wav,
    _snr_and_onsets,
    _spectrogram_png,
)
from backend.services.acoustic.ml import (
    _claude_acoustic,
    _claude_from_description,
    _coerce_claude_prediction,
    _gemini_classify_direct,
    _gemini_describe_audio,
)

logger = logging.getLogger(__name__)


MAX_ANALYSIS_SECONDS = 20
MIN_ANALYSIS_SECONDS = 1.5
MIN_RMS = 1e-4

# Save clips for farmer review when top-1 confidence is below this value (%).
FEEDBACK_CONFIDENCE_THRESHOLD = 60

METHODOLOGY_NOTE = (
    "Exploratory tool. Acoustic pest detection from spectrograms is an "
    "experimental signal — confirm pest identification by visual inspection "
    "before applying chemicals."
)


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


async def analyze(
    contents: bytes,
    normalized_crop: str,
    local_bundle,
    save_feedback_clip: Callable[[np.ndarray, int], str],
) -> AcousticResponse:
    """Run the full acoustic pipeline and return the response model.

    `local_bundle` is `request.app.state.acoustic_model` (PANNs bundle or
    None). `save_feedback_clip` is injected by the route so the Fernet
    encryptor and clip-dir location stay in the routes module.
    """
    if not contents:
        return _rejected(
            "Empty upload — no audio data received.",
            ["empty_upload"], 0.0, 0, None,
        )

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

    # 503 guard: if the local ML bundle failed to load AND no API keys are
    # configured, there is no acoustic backend at all — return a structured
    # 503 instead of silently producing an 'uncertain' result.
    # panns_model.MODEL_AVAILABLE / yamnet_model.MODEL_AVAILABLE are set by
    # their load() functions at startup; a False flag confirms that the failure
    # was a missing/corrupt weight file, not merely a missing bundle reference.
    if local_bundle is None and not settings_ref.GEMINI_API_KEY and not settings_ref.ANTHROPIC_API_KEY:
        from backend.ml import panns_model, yamnet_model
        if not panns_model.MODEL_AVAILABLE and not yamnet_model.MODEL_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "model_unavailable",
                    "message": "No acoustic ML models are loaded",
                },
            )
    ai_result: Optional[dict] = None
    ai_method = "uncertain"

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
            result["clip_id"] = save_feedback_clip(seg, rate)
        except Exception as _exc:
            logger.warning("acoustic: could not save feedback clip: %s", _exc)

    _cache_put(cache_key, result)
    return AcousticResponse(**result)
