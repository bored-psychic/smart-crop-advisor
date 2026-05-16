"""Soil analysis endpoint — deficiency detection + amendment recommendations."""

import json
import logging
import hashlib
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from anthropic import AsyncAnthropic

from backend.schemas.soil import SoilAnalysisRequest, SoilAnalysisResponse, NutrientDeficiency
from backend.services.soil_analyzer import (
    detect_deficiencies,
    get_amendments,
    get_compatible_crops,
)
from backend.services.soil_service import get_soil_type
from backend.core.cache import CacheManager
from backend.auth import require_api_key
from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/soil", tags=["Soil Analysis"])


def _soil_fingerprint(req: SoilAnalysisRequest) -> str:
    """Create a cache key fingerprint from soil parameters."""
    key_str = f"{req.N:.1f}_{req.P:.1f}_{req.K:.1f}_{req.ph:.1f}_{req.organic_matter_pct:.1f}"
    return hashlib.md5(key_str.encode()).hexdigest()


async def _generate_narrative(req: SoilAnalysisRequest, deficiencies: list[NutrientDeficiency]) -> str:
    """Use Claude Haiku to generate farmer-friendly advisory narrative."""
    try:
        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            logger.info("Haiku narrative skipped: ANTHROPIC_API_KEY not set, using fallback")
            return _fallback_narrative(req, deficiencies)

        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=10.0)

        # Format deficiencies for prompt
        deficiency_text = "\n".join([
            f"- {d.nutrient}: {d.current_value:.1f} (deficit: {d.deficit:.1f}, severity: {d.severity})"
            for d in deficiencies
        ]) if deficiencies else "No significant deficiencies detected."

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

Write your advice in simple Hindi/English mix (like you're speaking to a farmer). No markdown, no JSON, just plain text."""

        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )

        narrative = resp.content[0].text.strip() if resp.content else ""
        return narrative if narrative else "Soil quality is improving. Continue current practices."

    except ImportError:
        logger.warning("Anthropic SDK not installed, using fallback narrative")
        return _fallback_narrative(req, deficiencies)
    except Exception as exc:
        logger.warning(f"Haiku narrative generation failed: {exc}, using fallback")
        return _fallback_narrative(req, deficiencies)


def _fallback_narrative(req: SoilAnalysisRequest, deficiencies: list[NutrientDeficiency]) -> str:
    """Fallback narrative when Haiku is unavailable."""
    if not deficiencies:
        return "Your soil is well-balanced. Continue current farming practices and monitor annually."

    critical = [d for d in deficiencies if d.severity == 'high']
    if critical:
        critical_names = ", ".join([d.nutrient for d in critical[:2]])
        return f"Your soil is deficient in {critical_names}. Apply recommended amendments immediately for better yields. Retest soil in 30 days."

    return f"Your soil needs amendments for {len(deficiencies)} nutrients. Apply recommendations promptly."


@router.post("/analyze", response_model=SoilAnalysisResponse)
async def analyze_soil(
    req: SoilAnalysisRequest,
    request: Request,
    _: str = Depends(require_api_key),
):
    """Analyze soil and return deficiencies + amendment recommendations."""

    # Check cache first
    fingerprint = _soil_fingerprint(req)
    cache_key = f"soil_analysis:{fingerprint}"
    cached = await CacheManager.get(cache_key)
    if cached:
        logger.info(f"Soil analysis cache hit: {fingerprint}")
        return SoilAnalysisResponse(**cached)

    # Detect deficiencies
    deficiencies = detect_deficiencies(req)

    # Get amendments
    amendments = get_amendments(req, deficiencies)

    # Classify soil type (existing service)
    soil_info = get_soil_type(req.N, req.P, req.K, req.ph)
    soil_type = soil_info['soil_type']

    # Get compatible crops
    compatible_crops = get_compatible_crops(req)

    # Generate narrative via Haiku
    narrative = await _generate_narrative(req, deficiencies)

    # Build response
    response = SoilAnalysisResponse(
        deficiencies=deficiencies,
        amendments=amendments,
        soil_type=soil_type,
        narrative=narrative,
        compatible_crops=compatible_crops,
    )

    # Cache for 1 hour
    await CacheManager.set(cache_key, response.model_dump(), ttl=3600)

    return response
