# Acoustic ML Fallback Map

| Model | Weight file | Missing file behaviour |
|-------|-------------|------------------------|
| PANNs CNN14 (primary) | `backend/models/panns_head.joblib` | `load()` sets `MODEL_AVAILABLE=False`, logs `ERROR`, re-raises `FileNotFoundError`; `main.py` catches and sets `app.state.acoustic_model=None`; pipeline falls through to Gemini/Claude API. |
| YAMNet (secondary) | `backend/models/yamnet_head.joblib` | Same flag/error pattern; currently not loaded into `app.state`; present as future backbone swap target. |

If **all** local models are unavailable **and** `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` are both unset, `pipeline.analyze()` raises `HTTP 503 {"code":"model_unavailable","message":"No acoustic ML models are loaded"}`.
