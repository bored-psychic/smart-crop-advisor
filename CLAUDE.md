# KisanOS — Smart Crop Advisory System

## Anti-Hallucination Protocol (Read this first)
You are operating on a live agricultural advisory system. Farmers make real
decisions based on this system's output. A hallucinated import, a fabricated
function, or a wrong file path costs real crops and real money.

### Before writing ANY code:
1. **Verify, don't assume.** Run `ls`, `grep`, `cat` on the actual filesystem.
   If you haven't read the file, you don't know what's in it.
2. **Never invent imports.** Before writing `from X import Y`, grep the
   codebase for `Y`. If it doesn't exist, you don't import it.
3. **Never fabricate file paths.** The directory tree below is a reference —
   the filesystem is the source of truth. Run `ls` if unsure.
4. **Never invent API endpoints.** Read `backend/api/router.py` and the
   actual endpoint files in `backend/api/endpoints/` before calling any route.
5. **Never guess model artifact names.** Run
   `ls backend/*.pkl backend/*.h5 backend/*.tflite backend/*.npy` to see what
   actually exists on disk.
6. **Never assume a dependency is installed.** Check `requirements.txt` before
   using any import. If it's not listed, it's not available.

### The 95% Confidence Gate
You may not modify code until you can state:
- The exact file path and line number you are changing (verified by reading it).
- Every downstream consumer of the function or schema you are touching
  (verified by grepping for its name).
- A specific, runnable validation command to prove the change works.

If you cannot produce all three, stop and ask the user.

### Bug reports are not fix orders
When a user reports a bug: reproduce it first, provide root-cause analysis,
then wait for explicit go-ahead before writing a fix.

### When in doubt
Read the file. Read it again. Then read the file it imports from. The answer
is in the code, not in your training data.

---

## What this project is
KisanOS is an AI-powered decision support system for small and marginal farmers
in India. It provides localized crop recommendations, disease detection (via
TensorFlow or HSV pixel analysis fallback), market price forecasting, irrigation
advisory, field threat monitoring, and bioacoustic pest detection. The backend
serves predictions using Scikit-learn, Prophet, and optionally TensorFlow. The
bioacoustic feature interprets farm ambient sounds via the Anthropic API.

## Directory layout
```text
smart-crop-advisor/
├── backend/                        # FastAPI application (uvicorn entry: main.py)
│   ├── main.py                     # App factory, /health endpoint, mounts /api/v1
│   ├── api/
│   │   ├── router.py               # Registers: weather, market, crop, vision, acoustic
│   │   ├── schemas.py              # All Pydantic request/response models
│   │   └── endpoints/              # One file per feature
│   │       ├── weather.py
│   │       ├── market.py
│   │       ├── crop.py
│   │       ├── vision.py
│   │       └── acoustic.py
│   ├── core/
│   │   ├── config.py               # pydantic-settings, loads .env from project root
│   │   ├── cache.py                # CacheManager (Redis → in-memory dict fallback)
│   │   ├── models.py               # ModelManager (lru_cache loaders, returns None on miss)
│   │   ├── constants.py            # DISEASE_META lives here (not in models/)
│   │   ├── language.py
│   │   └── speech.py
│   ├── models/                     # Python wrappers — logic only, no artifacts
│   │   ├── crop_model.py
│   │   ├── price_model.py
│   │   └── vision_model.py         # DISEASE_META dict + display mappings
│   ├── services/                   # Business logic called by API endpoints
│   │   ├── weather.py              # OpenWeatherMap client
│   │   ├── market.py               # Market price data
│   │   ├── soil.py                 # Soil analysis
│   │   ├── vision.py               # Disease detection: TF model → HSV fallback
│   │   ├── acoustic.py             # Bioacoustic: spectrograms → Anthropic API
│   │   └── field_watch.py          # Field threat monitoring
│   ├── utils/
│   │   └── helpers.py
│   │
│   │  # ── ML Artifacts (loaded from backend/ root via core/models.py) ──
│   ├── crop_model.pkl              # Crop recommendation model
│   ├── scaler.pkl                  # Feature scaler for crop model
│   ├── label_encoder.pkl           # Label encoder for crop model
│   ├── disease_model.h5            # Keras disease detection model
│   ├── disease_model.tflite        # TFLite disease detection model
│   ├── class_names.npy             # Disease class labels
│   ├── acoustic_model.pkl          # Acoustic pest detection model
│   ├── price_model_*.json          # Prophet models (26 crops: apple → wheat)
│   └── price_data.csv              # Historical price dataset
│
├── frontend/                       # Streamlit dashboard
│   ├── app.py                      # Entry point
│   ├── api_client.py               # HTTP client to FastAPI backend
│   ├── ui_helpers.py               # Shared UI utilities
│   ├── tab1_crop.py                # Crop recommendation
│   ├── tab2_disease.py             # Disease detection
│   ├── tab3_market.py              # Market price forecast
│   ├── tab4_irrigation.py          # Irrigation advisory
│   ├── tab5_acoustic.py            # Bioacoustic analysis
│   └── tab6_field.py               # Field threat watch
│
├── web/                            # Legacy React interface (CDN Babel — bug fixes only)
│   ├── index.html
│   ├── tweaks-panel.jsx
│   └── components/
│       ├── app.jsx
│       └── garden.jsx
│
├── services/                       # Root-level services (legacy, separate from backend/)
│   ├── weather.py
│   ├── market.py
│   ├── soil.py
│   └── field_watch.py
├── core/                           # Root-level core (legacy, separate from backend/)
│   ├── language.py
│   └── speech.py
│
├── train_*.py                      # Model training scripts (6 files — do not run)
├── backend_client.py               # Standalone backend test client
├── old_app_backup.py               # Legacy monolith backup (~167KB — do not modify)
├── requirements.txt                # Single shared dependency file
├── .env                            # Secrets (never commit)
├── .env.example                    # Template (currently only has WEATHER_API_KEY)
├── .gitignore
├── .streamlit/config.toml
└── README.md

IMPORTANT: This tree was verified via `ls` on 2026-05-03. Always re-verify
against the filesystem before referencing any path.
```

## Environment setup
- **Python**: `3.10.12` — pinned. Do not upgrade. TF 2.13 breaks on 3.12.
  Prophet 1.1 has known issues on 3.11+.
- **Virtualenv**: `python -m venv venv && source venv/bin/activate`
- **Dependencies**: Single shared file at project root.
  ```bash
  pip install -r requirements.txt
  ```
  There are no separate backend/frontend requirements files. Do not create them.
- **Dependency conflict**: Prophet requires `numpy<1.24.0`. Installing a newer
  numpy silently breaks price forecasting — predictions return garbage values
  with no error. Never upgrade numpy.
- **TensorFlow**: Optional. NOT in `requirements.txt`. Install separately:
  `pip install tensorflow==2.13.*`. When TF is absent, disease detection
  degrades to the HSV pixel analysis fallback in `backend/services/vision.py`.
  This is by design — do not treat it as a bug.
- **Secrets**: `.env` at project root. Required keys (from `core/config.py`):
  ```
  WEATHER_API_KEY=           # OpenWeatherMap API key
  ANTHROPIC_API_KEY=         # Anthropic key for bioacoustic analysis
  REDIS_HOST=localhost       # Default: localhost
  REDIS_PORT=6379            # Default: 6379
  REDIS_DB=0                 # Default: 0
  REDIS_PASSWORD=            # Default: None
  CACHE_TTL_WEATHER=300      # seconds (Default: 300)
  CACHE_TTL_MARKET=43200     # seconds (Default: 43200)
  ```
  Note: `.env.example` currently only lists `WEATHER_API_KEY`. The authoritative
  list of env vars is in `backend/core/config.py:Settings`.

## Running locally
**Terminal 1 — Backend**
```bash
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
`--host 0.0.0.0` is intentional and non-negotiable — required for Docker
container networking and LAN access. Do not change to `127.0.0.1`.

**Terminal 2 — Frontend**
```bash
streamlit run frontend/app.py --server.port 8501
```

## Architecture & data flow
```
Streamlit (:8501)
    │  HTTP via frontend/api_client.py
    ▼
FastAPI (:8000)
    ├── /health              ← root-level health check
    └── /api/v1/             ← all feature routes
        ├── /weather
        ├── /market
        ├── /crop
        ├── /vision
        └── /acoustic

Internal call chain:
  api/endpoints/* → services/* → CacheManager.get/set() → external APIs
                  → core/models.py ModelManager → artifacts at backend/ root

web/ (standalone) ← Fetches :8000 directly. No shared state with Streamlit.
```

**ML model loading**: `ModelManager` in `backend/core/models.py` resolves
artifacts relative to `backend/` root (`_MODELS_DIR = parent of core/`).
Each loader is a `@staticmethod` with `@lru_cache(maxsize=1)`. Returns `None`
(or tuple of `None`s) when artifacts are missing. Endpoints MUST handle this.

**Vision / Disease detection**: `backend/services/vision.py` tries TF model
first. If TF is not installed or inference fails, it falls back to
`_hsv_analysis()` — a custom NumPy-based HSV (Hue-Saturation-Value) color
channel analysis that estimates disease by brown/yellow/green pixel ratios.
This is a real, intentional fallback. Do not remove or replace it.

**Bioacoustic**: `backend/services/acoustic.py` sends spectrogram data to
the Anthropic API. Uses `ANTHROPIC_API_KEY` from config. If the key is empty,
returns a fallback result. Model ID: use `claude-sonnet-4-6` for any new code.

## Caching (Redis)
Source of truth: `backend/core/cache.py`
- **Key format**: `{key_prefix}:{func.__name__}:{args}:{kwargs}`
  (built by the `@cache_response` decorator). Note: this uses raw `str()`
  of args/kwargs — be aware of non-deterministic string representations
  when passing complex objects.
- **TTL**: Set via `CACHE_TTL_WEATHER` (300s) and `CACHE_TTL_MARKET` (43200s)
  env vars. Decorator accepts custom `ttl` parameter.
- **Invalidation**: TTL expiry only. `CacheManager.delete(key)` exists for
  manual admin use.
- **Fallback**: If Redis is unavailable (import fails or connection refused),
  falls back to an in-memory Python dict with TTL tracking. Does not persist
  across restarts. Does not sync to Redis when connectivity recovers.

## Code style
- PEP 8. Max line length: 100.
- Type hints on all public functions and FastAPI endpoint signatures.
- Pydantic models for all request/response schemas (defined in
  `backend/api/schemas.py`). Never return raw `dict` from endpoints.
- No Black, Ruff, or other automated formatters — do not add them.

## Testing & validation
No automated test suite. Do not introduce Pytest or any framework without
explicit instruction. After any change, validate manually:

1. `curl http://localhost:8000/health` → `{"status": "ok", "timestamp": ...}`
2. `http://localhost:8000/docs` — verify schemas via Swagger UI
3. `http://localhost:8501` — Streamlit dashboard loads all 6 tabs

## Git conventions
- **Branches**: `feat/`, `fix/`, `chore/`, `docs/` prefixes off `main`
- **Commits**: Conventional Commits — `feat:`, `fix:`, `refactor:`,
  `docs:`, `chore:`
- **Never commit**: `.env`, `*.pkl`, `*.h5`, `*.tflite`, `*.npy`,
  `__pycache__/`, `venv/`, `*.pyc`, `.streamlit/secrets.toml`
  (see `.gitignore` for full list)

## Hard rules
1. **Model artifacts are read-only.** `.pkl`, `.h5`, `.tflite`, `.npy`, `.json`
   model files in `backend/` are pre-trained artifacts. Never retrain,
   overwrite, move, or rename them. The training scripts (`train_*.py` at root)
   are reference only — do not run them.

2. **Schema changes are breaking changes.** Modifying any model in
   `backend/api/schemas.py` will silently break the Streamlit client in
   `frontend/api_client.py`. Grep for the schema name across `frontend/`
   before changing any field.

3. **Model load failure must return 503.** `ModelManager` returns `None` on
   missing or corrupt artifacts. Every endpoint must handle `None` explicitly
   and return HTTP 503. Never let a `NoneType` error surface as a 500.

4. **TF is optional — HSV fallback is intentional.** `backend/services/vision.py`
   degrades from TensorFlow inference to HSV pixel analysis when TF is
   unavailable. This is a designed fallback using NumPy-based color channel
   math — not a bug and not a placeholder. Do not remove it. Do not replace
   it with scikit-learn unless explicitly instructed.

5. **`/web` is legacy — bug fixes only.** No new features. No `package.json`.
   No npm. No build steps. CDN Babel stays. New functionality goes in Streamlit.

6. **Dependency changes require conflict verification.** Before adding any
   package: confirm it doesn't violate `numpy<1.24.0` or conflict with
   existing pins in `requirements.txt`. Run `pip check` after any install.

7. **Cache key collision risk.** The `@cache_response` decorator in
   `backend/core/cache.py` builds keys from `str(args)` and `str(kwargs)`.
   If a service receives objects as arguments, ensure deterministic string
   representation or extract primitive identifiers before the cached call.

8. **Never fabricate what you can verify.** This rule overrides all others.
   If you are about to write a path, an import, a function name, or an
   endpoint URL — and you have not confirmed it exists by reading the
   filesystem — stop. Read it. Then write it.
