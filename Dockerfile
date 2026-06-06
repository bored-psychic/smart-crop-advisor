# KisanOS — Hugging Face Spaces (Docker SDK) image.
# Single container: FastAPI serves the API + the static web/ frontend on :7860.
FROM python:3.10.12-slim

# ── System deps ──────────────────────────────────────────────────────────
#  ffmpeg: required by pydub for non-WAV acoustic uploads (MP3/OGG/M4A/AMR).
#  wget/ca-certificates: fetch the CNN14 checkpoint at build time.
#  libgomp1: OpenMP runtime needed by torch / scikit-learn / lightgbm(prophet).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg wget ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user (HF Spaces convention; HOME must be writable) ───────────
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# ── Python deps ──────────────────────────────────────────────────────────
# Install CPU-only torch/torchaudio FIRST from the CPU wheel index so we do
# NOT pull the multi-GB CUDA build. Then the rest of the pins.
COPY --chown=user requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        torch==2.11.0 torchaudio==2.11.0 \
        --index-url https://download.pytorch.org/whl/cpu && \
    grep -ivE '^(torch|torchaudio)==' /tmp/requirements.txt > /tmp/req.rest.txt && \
    pip install --no-cache-dir -r /tmp/req.rest.txt

# ── Pre-stage CNN14 checkpoint into panns_inference's default cache ───────
# panns_model.py calls AudioTagging(checkpoint_path=None) which expects
# ~/panns_data/Cnn14_mAP=0.431.pth. Fetch at build time so there is no
# 312 MB download on first request.
RUN mkdir -p /home/user/panns_data && \
    wget -q -O "/home/user/panns_data/Cnn14_mAP=0.431.pth" \
        "https://zenodo.org/record/3987831/files/Cnn14_mAP%3D0.431.pth?download=1" && \
    wget -q -O /home/user/panns_data/class_labels_indices.csv \
        "https://raw.githubusercontent.com/qiuqiangkong/audioset_tagging_cnn/master/metadata/class_labels_indices.csv" && \
    chown -R user:user /home/user/panns_data

# ── App code ─────────────────────────────────────────────────────────────
WORKDIR /app
COPY --chown=user . /app

USER user
EXPOSE 7860

# Start the API; uvicorn binds 0.0.0.0:$PORT. Frontend is served by the app.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
