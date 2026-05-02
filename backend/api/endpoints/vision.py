from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image
import io
from services.vision import VisionService
from api.schemas import VisionResult

router = APIRouter()

@router.post("/diagnose", response_model=VisionResult)
async def diagnose_crop(
    file: UploadFile = File(...),
    crop_type: str = Form("Unknown"),
):
    MAX_FILE_SIZE = 10 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    try:
        img = Image.open(io.BytesIO(contents))
        result = await VisionService.analyze_image_pixels(img, image_bytes=contents, crop_type=crop_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
