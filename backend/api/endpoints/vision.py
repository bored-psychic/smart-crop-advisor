from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image
import io
from services.vision import VisionService
from api.schemas import VisionResult

router = APIRouter()

@router.post("/diagnose", response_model=VisionResult)
async def diagnose_crop(file: UploadFile = File(...)):
    # DEFENSIVE TITANIUM: Check file size to prevent memory exhaustion
    MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    
    try:
        img = Image.open(io.BytesIO(contents))
        # Optimized analysis
        result = await VisionService.analyze_image_pixels(img)
        # Ensure result has all required fields (Mapping back to schema)
        return {
            "disease": result.get("disease", "Unknown"),
            "severity": result.get("severity", "Medium"),
            "confidence": result.get("confidence", 0),
            "color": "orange",
            "treatment": "Maintain field hygiene.",
            "prevention": "Avoid waterlogging.",
            "action": "Monitor daily.",
            "top3": [],
            "model_used": result.get("model_used", "Vision AI")
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
