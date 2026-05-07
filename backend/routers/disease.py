"""Disease detection routes — image analysis + symptom lookup."""

import base64
import io
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File, Form
from PIL import Image, UnidentifiedImageError

from backend.schemas.disease import DiseaseResult, SymptomRequest, SymptomResponse
from core.disease_db import DISEASE_DB
from backend.auth import require_api_key
from backend.config import get_settings

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
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        img_b64 = base64.standard_b64encode(image_bytes).decode()
        resp = await client.messages.create(
            model="claude-sonnet-4-6",
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
async def analyze_image(
    request: Request,
    file: UploadFile = File(..., description="Leaf/stem/fruit photo (JPG/PNG/WebP/GIF)"),
    crop_type: str = Form("Unknown"),
    _: str = Depends(require_api_key),
):
    """Analyze uploaded crop image for disease detection."""
    settings = get_settings()
    contents = await file.read()

    if len(contents) > settings.MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Image too large ({len(contents) / 1_048_576:.1f} MB; "
                f"max {settings.MAX_IMAGE_BYTES // 1_048_576} MB)."
            ),
        )

    try:
        img = Image.open(io.BytesIO(contents))
        img.verify()
        img = Image.open(io.BytesIO(contents))
        img_format = (img.format or "").upper()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {exc}")

    media_type = _MIME_BY_FORMAT.get(img_format)
    if media_type is None:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image format '{img_format or 'unknown'}'. Use JPEG, PNG, WebP, or GIF.",
        )

    claude_result = await _claude_diagnose(contents, crop_type, media_type)
    if claude_result:
        return DiseaseResult(**claude_result)

    disease_bundle = request.app.state.disease_model
    if disease_bundle is None:
        raise HTTPException(status_code=503, detail="Disease model unavailable")
    result = disease_bundle.predict_from_image(img)

    return DiseaseResult(**result)


@router.post("/analyze-symptom", response_model=SymptomResponse)
async def analyze_symptom(
    req: SymptomRequest,
    _: str = Depends(require_api_key),
):
    """Look up disease/pest from crop + symptom combination."""
    if req.crop not in DISEASE_DB:
        raise HTTPException(status_code=404, detail=f"Crop '{req.crop}' not found in database")

    crop_diseases = DISEASE_DB[req.crop]
    if req.symptom not in crop_diseases:
        raise HTTPException(status_code=404, detail=f"Symptom not found for crop '{req.crop}'")

    data = crop_diseases[req.symptom]
    return SymptomResponse(
        disease=data['disease'],
        severity=data['severity'],
        disease_type=data.get('type', 'Disease'),
        treatment=data['treatment'],
        prevention=data['prevention'],
        crop=req.crop,
        symptom=req.symptom,
    )


@router.get("/crops")
async def list_crops(_: str = Depends(require_api_key)):
    """List all crops with available symptoms."""
    return {
        crop: list(symptoms.keys())
        for crop, symptoms in sorted(DISEASE_DB.items())
    }
