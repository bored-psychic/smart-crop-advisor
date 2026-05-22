"""Soil analysis endpoint — deficiency detection + amendment recommendations."""

import json
import logging
import hashlib
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from anthropic import AsyncAnthropic

from backend.schemas.soil import SoilAnalysisRequest, SoilAnalysisResponse, NutrientDeficiency, Amendment
from backend.services.soil_analyzer import (
    detect_deficiencies,
    get_amendments,
    get_compatible_crops,
)
from backend.services.soil_service import get_soil_type
from backend.services.i18n.dynamic import (
    tr_soil_type, tr_nutrient, tr_severity, tr_amendment_note, tr_crop,
    tr_fallback_narrative, lang_name,
)
from backend.core.cache import CacheManager
from backend.auth import require_user
from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/soil", tags=["Soil Analysis"])


def _soil_fingerprint(req: SoilAnalysisRequest, lang: str) -> str:
    """Create a cache key fingerprint from soil parameters + selected language.

    Language is part of the key because the cached response contains
    localized narrative / labels and must not be served across locales.
    """
    key_str = f"{req.N:.1f}_{req.P:.1f}_{req.K:.1f}_{req.ph:.1f}_{req.organic_matter_pct:.1f}_{lang}"
    return hashlib.md5(key_str.encode()).hexdigest()


async def _generate_narrative(
    req: SoilAnalysisRequest,
    deficiencies: list[NutrientDeficiency],
    lang: str,
) -> str:
    """Use Claude Haiku to generate farmer-friendly advisory narrative in the
    user's selected language. Falls back to a templated string when the API
    key is missing or the call fails."""
    try:
        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            logger.info("Haiku narrative skipped: ANTHROPIC_API_KEY not set, using fallback")
            return _fallback_narrative(req, deficiencies, lang)

        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=10.0)

        deficiency_text = "\n".join([
            f"- {d.nutrient}: {d.current_value:.1f} (deficit: {d.deficit:.1f}, severity: {d.severity})"
            for d in deficiencies
        ]) if deficiencies else "No significant deficiencies detected."

        target_language = lang_name(lang)

        prompt = f"""You are a soil health advisor for Indian farmers.
Given these soil test results, write a 2-3 sentence farmer-friendly advisory in simple language.
Focus on the most urgent actions to improve soil health.

Soil Parameters:
- Nitrogen: {req.N} kg/ha
- Phosphorus: {req.P} kg/ha
- Potassium: {req.K} kg/ha
- pH: {req.ph}
- Organic Matter: {req.organic_matter_pct}%

Identified Deficiencies:
{deficiency_text}

IMPORTANT: Write your advice ENTIRELY in {target_language}. Use the {target_language} script (Devanagari, Telugu script, Tamil script, etc. as appropriate). Do NOT mix English words except for technical fertilizer names (Urea, DAP, NPK, MOP) which farmers recognize. Keep it short, plain, and direct — no markdown, no JSON, just the advisory text."""

        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        narrative = resp.content[0].text.strip() if resp.content else ""
        return narrative if narrative else _fallback_narrative(req, deficiencies, lang)

    except ImportError:
        logger.warning("Anthropic SDK not installed, using fallback narrative")
        return _fallback_narrative(req, deficiencies, lang)
    except Exception as exc:
        logger.warning(f"Haiku narrative generation failed: {exc}, using fallback")
        return _fallback_narrative(req, deficiencies, lang)


def _fallback_narrative(
    req: SoilAnalysisRequest,
    deficiencies: list[NutrientDeficiency],
    lang: str,
) -> str:
    """Fallback narrative when Haiku is unavailable. Localized via the
    `FALLBACK_NARRATIVE` table in `backend.services.i18n.dynamic`."""
    if not deficiencies:
        return tr_fallback_narrative('balanced', lang)

    critical = [d for d in deficiencies if d.severity == 'high']
    if critical:
        critical_names = ", ".join([tr_nutrient(d.nutrient, lang) for d in critical[:2]])
        return tr_fallback_narrative('critical_deficient', lang, nutrients=critical_names)

    return tr_fallback_narrative('mild_deficient', lang, count=len(deficiencies))


def _localize_deficiencies(
    deficiencies: list[NutrientDeficiency], lang: str,
) -> list[NutrientDeficiency]:
    """Return a new list with `nutrient` and `severity` translated."""
    return [
        NutrientDeficiency(
            nutrient=tr_nutrient(d.nutrient, lang),
            current_value=d.current_value,
            optimal_min=d.optimal_min,
            optimal_max=d.optimal_max,
            deficit=d.deficit,
            severity=tr_severity(d.severity, lang),
        )
        for d in deficiencies
    ]


def _localize_amendments(amendments: list[Amendment], lang: str) -> list[Amendment]:
    """Translate the `notes` field on each amendment. Fertilizer trade names
    (Urea, DAP, MOP, etc.) stay in English — farmers recognize them by name."""
    return [
        Amendment(
            name=a.name,
            deficiency_target=a.deficiency_target,
            dose_kg_per_acre=a.dose_kg_per_acre,
            dose_kg_per_hectare=a.dose_kg_per_hectare,
            dose_tonnes_per_acre=a.dose_tonnes_per_acre,
            dose_tonnes_per_hectare=a.dose_tonnes_per_hectare,
            time_to_effect_days=a.time_to_effect_days,
            application_method=a.application_method,
            notes=tr_amendment_note(a.notes, lang),
        )
        for a in amendments
    ]


@router.post("/analyze", response_model=SoilAnalysisResponse)
async def analyze_soil(
    req: SoilAnalysisRequest,
    request: Request,
    _=Depends(require_user),
):
    """Analyze soil and return deficiencies + amendment recommendations."""

    lang = getattr(request.state, "lang", "en")

    # Cache key now includes lang — localized payloads must not cross locales.
    fingerprint = _soil_fingerprint(req, lang)
    cache_key = f"soil_analysis:{fingerprint}"
    cached = await CacheManager.get(cache_key)
    if cached:
        logger.info(f"Soil analysis cache hit: {fingerprint}")
        return SoilAnalysisResponse(**cached)

    deficiencies = detect_deficiencies(req)
    amendments = get_amendments(req, deficiencies)

    soil_info = get_soil_type(req.N, req.P, req.K, req.ph)
    soil_type_en = soil_info['soil_type']

    compatible_crops_en = get_compatible_crops(req)

    # Haiku narrative built BEFORE we localize deficiencies — it needs the
    # canonical N/P/K/pH codes to reason about, not the translated labels.
    narrative = await _generate_narrative(req, deficiencies, lang)

    response = SoilAnalysisResponse(
        deficiencies=_localize_deficiencies(deficiencies, lang),
        amendments=_localize_amendments(amendments, lang),
        soil_type=tr_soil_type(soil_type_en, lang),
        narrative=narrative,
        compatible_crops=[tr_crop(c, lang) for c in compatible_crops_en],
    )

    await CacheManager.set(cache_key, response.model_dump(), ttl=3600)

    return response
