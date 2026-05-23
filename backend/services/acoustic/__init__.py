"""Acoustic analysis service package.

Split from `backend.routers.acoustic` (P2 Task 5). The router now contains
only route handlers + feedback-clip Fernet helper + the PEST_META / label
allowlist; everything else lives here:

  - dsp.py       audio decode/encode, LUFS, framed RMS SNR, mel-spec PNG
  - cache.py     bounded LRU response cache (cachetools)
  - ml.py        Claude / Gemini fan-out + result normalization
  - pipeline.py  load → normalize → DSP → ML → cache orchestration
"""
