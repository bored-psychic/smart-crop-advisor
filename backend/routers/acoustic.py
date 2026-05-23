"""Acoustic pest detection router.

Thin route layer over `backend.services.acoustic.pipeline`. The DSP,
caching, and Claude/Gemini fan-out live in the service package; this
module holds only HTTP plumbing, the feedback-clip Fernet helper, and the
label allowlist used by the feedback endpoint.
"""

import datetime as dt
import io
import json
import logging
import uuid
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wav
from pydantic import BaseModel

from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from backend.schemas.errors import http_error

from backend.auth import require_api_key, require_user
from backend.config import get_settings
from backend.core.constants import PEST_META
from backend.middleware.rate_limit import limiter
from backend.ml.acoustic_model import _normalize_crop_type
from backend.schemas.acoustic import AcousticResponse
from backend.services import dosage_service
from backend.services.acoustic import pipeline
# Re-export so existing imports (and the contract test in
# tests/test_acoustic_pest_names.py) keep working without churn.
from backend.services.acoustic.ml import (  # noqa: F401
    _coerce_claude_prediction,
    _normalize_pest_name,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/acoustic", tags=["Acoustic Pest Detection"])

# Active-learning feedback storage. Clips are saved as 16-bit WAV; feedback
# entries are written as JSONL. The retrain script picks these up.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FEEDBACK_CLIPS_DIR = _REPO_ROOT / "data" / "feedback_clips"
FEEDBACK_QUEUE_FILE = _REPO_ROOT / "data" / "feedback_queue" / "feedback.jsonl"
AUDIO_SAMPLES_DIR = _REPO_ROOT / "data" / "audio_samples"

PEST_ICONS = {name: meta['icon'] for name, meta in PEST_META.items()}


# ── Feedback / active-learning helpers ────────────────────────────────────────

def _save_feedback_clip(pcm: np.ndarray, rate: int) -> str:
    """Encrypt + write decoded PCM to feedback_clips/ and return clip UUID.

    P1 Task 3: clips are Fernet-encrypted at rest so a leaked
    `data/feedback_clips/` directory does not yield playable farmer
    recordings. The retrain pipeline (scripts/retrain_from_feedback.py)
    must Fernet-decrypt before feeding clips back into training.
    """
    from cryptography.fernet import Fernet
    FEEDBACK_CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    clip_id = str(uuid.uuid4())
    out = FEEDBACK_CLIPS_DIR / f"{clip_id}.wav"
    int16 = np.clip(pcm * 32767.0, -32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    wav.write(buf, rate, int16)
    settings = get_settings()
    encrypted = Fernet(settings.FERNET_KEY.encode()).encrypt(buf.getvalue())
    out.write_bytes(encrypted)
    return clip_id


# Authoritative label allowlist for feedback endpoint path-component validation.
# Derived from PEST_META — the same set the model can emit — plus the
# open-vocabulary names the Claude/Gemini API pipeline may return.
# Any corrected_label that is not in this set is rejected to prevent path traversal.
VALID_LABELS: frozenset[str] = frozenset(PEST_META.keys())


class _FeedbackBody(BaseModel):
    clip_id: str
    corrected_label: str
    predicted_label: str = ""
    confidence: int = 0
    crop_type: str = "Unknown"
    analysis_method: str = "panns"


@router.post("/feedback")
async def submit_feedback(body: _FeedbackBody, _: str = Depends(require_api_key)):
    """Record a farmer label correction and move the clip to the training queue.

    Called by the frontend when a user submits the "Help improve the AI" widget.
    The clip UUID must match a file already saved in FEEDBACK_CLIPS_DIR (created
    at analysis time when confidence was below FEEDBACK_CONFIDENCE_THRESHOLD).
    If the corrected_label is "skip" the clip is left in place but not queued.
    """
    label = (body.corrected_label or "").strip()
    if not label or label.lower() == "skip":
        return {"status": "skipped"}

    # Path traversal prevention: only allow labels from the authoritative
    # PEST_META allowlist. A supplied label like "../../etc/passwd" would
    # otherwise escape AUDIO_SAMPLES_DIR when used as a path component.
    if label not in VALID_LABELS:
        raise http_error(
            400,
            "invalid_label",
            f"Unknown label: {label!r}. Must be one of: {sorted(VALID_LABELS)}",
        )

    clip_src = FEEDBACK_CLIPS_DIR / f"{body.clip_id}.wav"
    if not clip_src.exists():
        raise http_error(404, "clip_not_found", "clip_id not found")

    # Copy clip to the matching training-data folder so the next retrain run
    # picks it up automatically via collect_dataset(). Clips are Fernet-
    # encrypted at rest (P1 Task 3), so decrypt before writing the
    # plaintext WAV into the training set.
    from cryptography.fernet import Fernet, InvalidToken
    settings = get_settings()
    try:
        decrypted = Fernet(settings.FERNET_KEY.encode()).decrypt(
            clip_src.read_bytes()
        )
    except InvalidToken:
        # Legacy unencrypted clip from before P1 Task 3 — accept as-is.
        decrypted = clip_src.read_bytes()
    dest_dir = AUDIO_SAMPLES_DIR / label
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"feedback_{body.clip_id}.wav"
    dest.write_bytes(decrypted)

    # Append to JSONL queue for audit / statistics.
    FEEDBACK_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": dt.datetime.utcnow().isoformat() + "Z",
        "clip_id": body.clip_id,
        "predicted_label": body.predicted_label,
        "corrected_label": label,
        "confidence": body.confidence,
        "crop_type": body.crop_type,
        "analysis_method": body.analysis_method,
    }
    with FEEDBACK_QUEUE_FILE.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")

    logger.info(
        "feedback: clip %s labelled as '%s' (was '%s' @ %d%%)",
        body.clip_id, label, body.predicted_label, body.confidence,
    )
    return {"status": "ok", "dest": str(dest)}


@router.post("/analyze", response_model=AcousticResponse)
@limiter.limit("20/hour")
async def analyze_audio(
    request: Request,
    file: UploadFile = File(..., description="Field audio recording (WAV/MP3/OGG)"),
    crop_type: str = Form("Unknown"),
    _user=Depends(require_user),
):
    """Analyze audio for pest signatures — Claude bioacoustics first, RF fallback."""
    normalized_crop = _normalize_crop_type(crop_type)
    contents = await file.read()
    return await pipeline.analyze(
        contents=contents,
        normalized_crop=normalized_crop,
        local_bundle=request.app.state.acoustic_model,
        save_feedback_clip=_save_feedback_clip,
        dosage_lookup=dosage_service.lookup,
    )
