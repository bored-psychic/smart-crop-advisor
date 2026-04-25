"""Disease detection routes — image analysis + symptom lookup."""

from fastapi import APIRouter, Request, Depends, UploadFile, File
from backend.schemas.disease import DiseaseResult, SymptomRequest, SymptomResponse
from backend.data.disease_db import DISEASE_DB
from backend.auth import require_api_key

router = APIRouter(prefix="/api/disease", tags=["Disease Detection"])


@router.post("/analyze-image", response_model=DiseaseResult)
async def analyze_image(
    request: Request,
    file: UploadFile = File(..., description="Leaf/stem/fruit photo (JPG/PNG/WebP)"),
    _: str = Depends(require_api_key),
):
    """Analyze uploaded crop image for disease detection."""
    from PIL import Image
    import io

    contents = await file.read()
    img = Image.open(io.BytesIO(contents))

    disease_bundle = request.app.state.disease_model
    result = disease_bundle.predict_from_image(img)

    return DiseaseResult(**result)


@router.post("/analyze-symptom", response_model=SymptomResponse)
async def analyze_symptom(
    req: SymptomRequest,
    _: str = Depends(require_api_key),
):
    """Look up disease/pest from crop + symptom combination."""
    if req.crop not in DISEASE_DB:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Crop '{req.crop}' not found in database")

    crop_diseases = DISEASE_DB[req.crop]
    if req.symptom not in crop_diseases:
        from fastapi import HTTPException
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
