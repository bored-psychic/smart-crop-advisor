"""Disease detection routes — image analysis + symptom lookup."""

import base64
import io
import json
import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, Query
from backend.schemas.errors import http_error
from PIL import Image, UnidentifiedImageError

from backend.schemas.disease import DiseaseResult, SymptomRequest, SymptomResponse, TreatmentPriceRequest, TreatmentPriceResponse
from core.disease_db import DISEASE_DB
from backend.auth import require_api_key, require_user, require_user_or_api_key
from backend.config import get_settings
from backend.middleware.rate_limit import limiter
from backend.services import dosage_service

# Authoritative crop allowlist for the analyze-image endpoint (same source of
# truth as the symptom database). "Unknown" is always accepted as the
# no-selection sentinel.
_VALID_CROP_TYPES: frozenset[str] = frozenset(DISEASE_DB.keys())

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/disease", tags=["Disease Detection"])

_MIME_BY_FORMAT = {
    "JPEG": "image/jpeg",
    "PNG":  "image/png",
    "WEBP": "image/webp",
    "GIF":  "image/gif",
}


async def _claude_diagnose(image_bytes: bytes, crop_type: str, media_type: str) -> Optional[dict]:
    """Try Claude Vision first; return None on any failure (logged)."""
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        logger.info("Claude vision skipped: ANTHROPIC_API_KEY not set")
        return None

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=15.0)
        img_b64 = base64.standard_b64encode(image_bytes).decode()
        resp = await client.messages.create(
            model="claude-opus-4-7",
            max_tokens=800,
            system=[{
                "type": "text",
                "text": (
                    "You are a plant pathologist diagnosing crop diseases, nutrient "
                    "deficiencies, and pest damage from photos. Be specific and accurate.\n\n"
                    "Respond ONLY with valid JSON, no markdown fences:\n"
                    '{"disease":"Full disease or condition name","severity":"High|Medium|Low|None",'
                    '"confidence":82,"color":"red|orange|green",'
                    '"treatment":"specific treatment with product name and dose",'
                    '"prevention":"how to prevent recurrence",'
                    '"action":"single most urgent action right now",'
                    '"top3":[["Condition1",82],["Condition2",12],["Condition3",6]],'
                    '"model_used":"Claude Vision API"}'
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
                            "media_type": media_type,
                            "data": img_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": f"Diagnose this {crop_type} plant image. JSON only.",
                    },
                ],
            }],
        )
    except ImportError:
        logger.warning("Claude vision skipped: anthropic SDK not installed")
        return None
    except Exception as exc:
        logger.warning("Claude vision API call failed: %s: %s", type(exc).__name__, exc)
        return None

    try:
        return json.loads(resp.content[0].text)
    except (json.JSONDecodeError, IndexError, AttributeError, KeyError) as exc:
        logger.warning("Claude vision response parse failed: %s: %s", type(exc).__name__, exc)
        return None


@router.post("/analyze-image", response_model=DiseaseResult)
@limiter.limit("20/hour")
async def analyze_image(
    request: Request,
    file: UploadFile = File(..., description="Leaf/stem/fruit photo (JPG/PNG/WebP/GIF)"),
    crop_type: str = Form("Unknown"),
    _user=Depends(require_user),
):
    """Analyze uploaded crop image for disease detection."""
    # Validate crop_type against the known allowlist to prevent injection of
    # arbitrary strings into AI prompts and downstream processing.
    if crop_type != "Unknown" and crop_type not in _VALID_CROP_TYPES:
        raise http_error(
            422,
            "invalid_crop_type",
            f"Unsupported crop_type: {crop_type!r}. "
            f"Valid values: {sorted(_VALID_CROP_TYPES)} or 'Unknown'.",
        )

    settings = get_settings()
    contents = await file.read()

    if len(contents) > settings.MAX_IMAGE_BYTES:
        raise http_error(
            413,
            "image_too_large",
            f"Image too large ({len(contents) / 1_048_576:.1f} MB; "
            f"max {settings.MAX_IMAGE_BYTES // 1_048_576} MB).",
        )

    try:
        img = Image.open(io.BytesIO(contents))
        img.verify()
        img = Image.open(io.BytesIO(contents))
        img_format = (img.format or "").upper()
    except (UnidentifiedImageError, OSError) as exc:
        raise http_error(400, "invalid_image", f"Invalid image file: {exc}")

    media_type = _MIME_BY_FORMAT.get(img_format)
    if media_type is None:
        raise http_error(
            415,
            "unsupported_media_type",
            f"Unsupported image format '{img_format or 'unknown'}'. Use JPEG, PNG, WebP, or GIF.",
        )

    claude_result = await _claude_diagnose(contents, crop_type, media_type)
    if claude_result:
        result_obj = DiseaseResult(**claude_result)
        try:
            result_obj.dosage_advice = await dosage_service.lookup(
                pest_id=result_obj.disease,
                crop=crop_type,
                crop_stage_days=0,
                area_acres=1.0,
                state=None,
            )
        except Exception:
            pass
        return result_obj

    disease_bundle = request.app.state.disease_model
    if disease_bundle is None:
        raise http_error(503, "model_unavailable", "Disease model unavailable")
    rgb_array = np.asarray(img.convert('RGB'), dtype=np.uint8)
    result = disease_bundle.predict_from_image(rgb_array)

    result_obj = DiseaseResult(**result)
    try:
        result_obj.dosage_advice = await dosage_service.lookup(
            pest_id=result_obj.disease,
            crop=crop_type,
            crop_stage_days=0,
            area_acres=1.0,
            state=None,
        )
    except Exception:
        pass
    return result_obj


@router.post("/analyze-symptom", response_model=SymptomResponse)
async def analyze_symptom(
    req: SymptomRequest,
    _=Depends(require_user_or_api_key),
):
    """Look up disease/pest from crop + symptom combination."""
    if req.crop not in DISEASE_DB:
        raise http_error(404, "crop_not_found", f"Crop '{req.crop}' not found in database")

    crop_diseases = DISEASE_DB[req.crop]
    if req.symptom not in crop_diseases:
        raise http_error(404, "symptom_not_found", f"Symptom not found for crop '{req.crop}'")

    data = crop_diseases[req.symptom]
    response = SymptomResponse(
        disease=data['disease'],
        severity=data['severity'],
        disease_type=data.get('type', 'Disease'),
        treatment=data['treatment'],
        prevention=data['prevention'],
        crop=req.crop,
        symptom=req.symptom,
    )
    try:
        response.dosage_advice = await dosage_service.lookup(
            pest_id=data['disease'],
            crop=req.crop,
            crop_stage_days=0,
            area_acres=1.0,
            state=None,
        )
    except Exception:
        pass
    return response


@router.post("/treatment-price", response_model=TreatmentPriceResponse)
async def estimate_treatment_price(
    req: TreatmentPriceRequest,
    _=Depends(require_user_or_api_key),
):
    """Estimate treatment/fertilizer cost in INR using Claude Haiku."""
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        raise http_error(503, "api_key_not_configured", "Anthropic API key not configured")

    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=10.0)

    prompt = (
        f"A farmer in India has {req.area_acres} acres of {req.crop_type}. "
        f"Diagnosed: {req.disease}. Recommended treatment: {req.treatment}.\n\n"
        "Estimate the total cost in Indian Rupees (INR) for this treatment covering the full field. "
        "Include chemical/fertilizer cost and typical labor. Use current Indian market rates.\n\n"
        "Respond ONLY with valid JSON (no markdown fences):\n"
        '{"cost_range":"₹X,XXX – ₹Y,YYY","per_acre_inr":N,"total_inr":N,"notes":"brief note"}'
    )

    try:
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "{"},
            ],
        )
        if not resp.content:
            raise http_error(503, "ai_empty_response", "AI provider returned empty response")
        raw = "{" + resp.content[0].text
        # strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        logger.info("Treatment price raw response: %s", raw)
        data = json.loads(raw)
        return TreatmentPriceResponse(**data)
    except Exception as exc:
        logger.warning("Treatment price estimation failed: %s", exc)
        raise http_error(502, "treatment_price_failed", "Could not estimate treatment price")


@router.get("/crops")
async def list_crops(
    detailed: bool = Query(False),
    _user=Depends(require_user),
):
    """List all crops with available symptoms. Use ?detailed=true for full symptom metadata."""
    if not detailed:
        return {
            crop: list(symptoms.keys())
            for crop, symptoms in sorted(DISEASE_DB.items())
        }
    # Detailed: return [{symptom, disease, severity, type}] per crop
    return {
        crop: [
            {
                "symptom": symptom,
                "disease": data.get("disease", ""),
                "severity": data.get("severity", "Medium"),
                "type": data.get("type", "Disease"),
            }
            for symptom, data in symptoms.items()
        ]
        for crop, symptoms in sorted(DISEASE_DB.items())
    }
