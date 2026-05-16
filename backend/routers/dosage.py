from fastapi import APIRouter, Depends
from backend.schemas.dosage import DosageRequest, DosageAdvice
from backend.services import dosage_service
from backend.auth import require_api_key

router = APIRouter(prefix="/api/dosage", tags=["dosage"])


@router.post("/recommend", response_model=DosageAdvice)
async def recommend_dosage(
    req: DosageRequest,
    _: str = Depends(require_api_key),
):
    return await dosage_service.lookup(
        pest_id=req.pest_id,
        crop=req.crop,
        crop_stage_days=req.crop_stage_days,
        area_acres=req.area_acres,
        state=req.state,
    )
