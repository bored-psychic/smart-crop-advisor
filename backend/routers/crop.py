"""POST /api/crop/recommend — Crop recommendation from soil + climate data."""

from fastapi import APIRouter, HTTPException, Request, Depends
from backend.schemas.crop import CropRecommendRequest, CropRecommendResponse, CropPrediction, SoilInfo
from backend.services.soil_service import get_soil_type
from backend.core.constants import CROP_EMOJI, CROP_TIPS
from backend.auth import require_api_key

router = APIRouter(prefix="/api/crop", tags=["Crop Recommender"])


@router.post("/recommend", response_model=CropRecommendResponse)
async def recommend_crop(
    req: CropRecommendRequest,
    request: Request,
    _: str = Depends(require_api_key),
):
    """Run Random Forest crop prediction and soil analysis."""
    crop_bundle = request.app.state.crop_model
    if crop_bundle is None:
        raise HTTPException(status_code=503, detail="Crop model unavailable")
    result = crop_bundle.predict(
        req.N, req.P, req.K,
        req.temperature, req.humidity, req.ph, req.rainfall
    )

    top_crop = result['top_crop']
    soil = get_soil_type(req.N, req.P, req.K, req.ph)

    return CropRecommendResponse(
        top_crop=CropPrediction(
            crop=top_crop,
            confidence=result['top_conf'],
            emoji=CROP_EMOJI.get(top_crop.lower(), '🌱'),
        ),
        alternatives=[
            CropPrediction(
                crop=c,
                confidence=conf,
                emoji=CROP_EMOJI.get(c.lower(), '🌱'),
            )
            for c, conf in result['alternatives']
        ],
        tip=CROP_TIPS.get(top_crop.lower(), ''),
        soil=SoilInfo(
            soil_type=soil['soil_type'],
            advice=soil['advice'],
            indicator=soil['indicator'],
        ),
        all_probabilities=dict(
            sorted(result['all_probs'].items(), key=lambda kv: -kv[1])[:5]
        ),
    )
