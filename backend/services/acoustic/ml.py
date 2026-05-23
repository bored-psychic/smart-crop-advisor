"""Claude / Gemini fan-out for the acoustic pipeline.

Three dispatch helpers (`_claude_acoustic`, `_gemini_describe_audio`,
`_claude_from_description`, `_gemini_classify_direct`) plus the result
normalization layer (`_normalize_pest_name`, `_coerce_claude_prediction`)
that turns a raw AI JSON payload into the schema the route returns.

The fallback ordering and prompts are unchanged from the pre-refactor
router — this module is a move, not a rewrite.
"""

import base64
import json
import logging
from typing import Optional

from fastapi import HTTPException

from backend.config import get_settings
from backend.core.constants import PEST_META

logger = logging.getLogger(__name__)


_VALID_PESTS = list(PEST_META.keys())
_VALID_PESTS_LOWER = {name.lower(): name for name in _VALID_PESTS}

# Sanity floor: drops empty hallucinations only. Claude's own calibration
# rules cap weak matches at 30-55, so any value above this is treated as a
# real call rather than second-guessed here.
_CLAUDE_MIN_CONFIDENCE = 5


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

        if not resp.content:
            raise HTTPException(status_code=503, detail="AI provider returned empty response")

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

        if not resp.content:
            raise HTTPException(status_code=503, detail="AI provider returned empty response")

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
