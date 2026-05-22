"""POST /api/crop/recommend — Crop recommendation from soil + climate data."""

from fastapi import APIRouter, HTTPException, Request, Depends
from backend.schemas.crop import CropRecommendRequest, CropRecommendResponse, CropPrediction, SoilInfo
from backend.services.soil_service import get_soil_type
from backend.services.i18n.dynamic import (
    tr_crop, tr_crop_tip, tr_soil_type, tr_soil_advice,
)
from backend.core.constants import CROP_EMOJI, CROP_TIPS
from backend.auth import require_user_or_api_key

router = APIRouter(prefix="/api/crop", tags=["Crop Recommender"])


@router.post("/recommend", response_model=CropRecommendResponse)
async def recommend_crop(
    req: CropRecommendRequest,
    request: Request,
    _=Depends(require_user_or_api_key),
):
    """Run Random Forest crop prediction and soil analysis."""
    crop_bundle = request.app.state.crop_model
    if crop_bundle is None:
        raise HTTPException(status_code=503, detail="Crop model unavailable")

    lang = getattr(request.state, "lang", "en")

    result = crop_bundle.predict(
        req.N, req.P, req.K,
        req.temperature, req.humidity, req.ph, req.rainfall
    )

    top_crop = result['top_crop']
    soil = get_soil_type(req.N, req.P, req.K, req.ph)
    en_tip = CROP_TIPS.get(top_crop.lower(), '')

    return CropRecommendResponse(
        top_crop=CropPrediction(
            crop=tr_crop(top_crop, lang),
            confidence=result['top_conf'],
            emoji=CROP_EMOJI.get(top_crop.lower(), '🌱'),
        ),
        alternatives=[
            CropPrediction(
                crop=tr_crop(c, lang),
                confidence=conf,
                emoji=CROP_EMOJI.get(c.lower(), '🌱'),
            )
            for c, conf in result['alternatives']
        ],
        tip=tr_crop_tip(top_crop, lang, en_tip),
        soil=SoilInfo(
            soil_type=tr_soil_type(soil['soil_type'], lang),
            advice=tr_soil_advice(soil['advice'], lang),
            indicator=soil['indicator'],
        ),
        all_probabilities=dict(
            sorted(result['all_probs'].items(), key=lambda kv: -kv[1])[:5]
        ),
    )
