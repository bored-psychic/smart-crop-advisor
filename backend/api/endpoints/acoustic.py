from fastapi import APIRouter, UploadFile, File, HTTPException
from services.acoustic import AcousticService
from api.schemas import AcousticResult

router = APIRouter()

@router.post("/analyze", response_model=AcousticResult)
async def analyze_acoustic(file: UploadFile = File(...)):
    # DEFENSIVE TITANIUM: 20MB Max for audio recordings
    MAX_SIZE = 20 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Audio file too large")
    
    result = await AcousticService.analyze_audio(contents)
    return result
