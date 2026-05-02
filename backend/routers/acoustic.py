"""Acoustic pest detection router."""

from fastapi import APIRouter, Request, Depends, UploadFile, File
from backend.schemas.acoustic import AcousticResponse
from backend.ml.acoustic_model import extract_features
from backend.auth import require_api_key

router = APIRouter(prefix="/api/acoustic", tags=["Acoustic Pest Detection"])


@router.post("/analyze", response_model=AcousticResponse)
async def analyze_audio(
    request: Request,
    file: UploadFile = File(..., description="Field audio recording (WAV/MP3/OGG)"),
    _: str = Depends(require_api_key),
):
    """Analyze audio for pest signatures using Random Forest ML."""
    contents = await file.read()
    acoustic_bundle = request.app.state.acoustic_model

    features = extract_features(contents, file.filename or "audio")

    if features is not None:
        result = acoustic_bundle.predict(features)
        return AcousticResponse(**result)

    # Feature extraction failed
    return AcousticResponse(
        pest='Analysis Incomplete',
        severity='low',
        confidence=0,
        freq_range='N/A',
        pattern='Could not decode audio',
        energy_level='Unknown',
        action='Audio format could not be decoded. Please upload a WAV file.',
        icon='⚠️',
        top3=[],
        ml_used=False,
    )
