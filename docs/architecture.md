# Architecture Overview

## What This App Does

The Smart Crop Advisory System provides AI-powered recommendations to Indian farmers on six key decisions:

1. **Crop Recommendation** — analyzes soil (N/P/K), climate (temperature/humidity/rainfall), and pH to recommend the best crop
2. **Disease Detection** — identifies 38 plant diseases from leaf images using transfer learning
3. **Market Price Forecast** — predicts mandi (market) prices 30 days out for planning sales
4. **Irrigation Advisor** — calculates water requirement (FAO-56 formula) given weather data
5. **Acoustic Pest Detection** — analyzes farm audio for pest activity, pollinator presence, and stress signals
6. **Field Watch** — aggregates satellite fire data (NASA FIRMS), flood warnings, and air quality into a single farm health view

Data flows through a **modular backend** (FastAPI) that decouples API routes from business logic services and ML inference, allowing graceful degradation when external APIs fail or models are unavailable.

## Request → Response Flow

Typical request path:

```
Browser / Mobile Client
  ↓
  GET/POST http://localhost:8000/api/{crop,disease,market,etc}
  + Authorization: Bearer <JWT token>
  ↓
FastAPI Router (backend/routers/{crop,disease,market,etc}.py)
  ├─ Validate auth via require_user or require_api_key dependency
  ├─ Parse Accept-Language header (via LocaleMiddleware)
  ├─ Validate & deserialize request body (Pydantic models)
  ↓
Service Layer (backend/services/{crop_service,disease_service,etc}.py)
  ├─ Fetch external data (API calls with error handling and caching)
  ├─ Log with PII redaction (masked phones/endpoints)
  ↓
ML / Data Layer (backend/ml/{crop_model,disease_model,acoustic_model}.py)
  ├─ Load pre-trained models (Random Forest, TFLite, PyTorch)
  ├─ Invoke inference (e.g., crop_model.predict(...) returns {top_crop, alternatives})
  ├─ Fallback to degraded mode if model unavailable
  ↓
Response Assembly
  ├─ Translate dynamic text (crop names, soil advice) via i18n.dynamic
  ├─ Shape into Pydantic response model
  ├─ Add HTTP status and headers (security headers from SecurityHeadersMiddleware)
  ↓
Client
```

Each service is independently testable; mocking external HTTP calls with `respx` and auth with `auth_headers` fixture from `tests/conftest.py`.

## Internationalization (i18n)

The app supports 5 languages: English (en), Hindi (hi), Tamil (ta), Telugu (te), Kannada (kn).

**Locale detection:**
1. LocaleMiddleware parses the `Accept-Language` HTTP header (e.g., `hi-IN,hi;q=0.9,en;q=0.8`)
2. Extracts the first language code matching a supported language
3. Defaults to English if no match
4. Stores two-letter code on `request.state.lang`

**Translation in handlers:**
- Static strings live in `web/lib/bundles/{en,hi,ta,te,kn}.json` (JSON key→value)
- Dynamic content (crop names, disease names, soil advice) uses `backend/services/i18n/dynamic.py`:
  - `tr_crop(crop_name, lang)` — translates "wheat" → "गेहूं" (Hindi)
  - `tr_disease(disease_name, lang)` — translates disease labels
  - Each function is a lookup table; missing keys return a placeholder and log a warning in strict mode

## PII Encryption & Privacy

**Two-layer protection for phone numbers:**

1. **Lookup hash (peppered SHA-256):**
   - Stored in `alert_subscriptions.phone_hash` and `webpush_subscriptions.phone_hash`
   - Computed: `sha256(phone + APP_PEPPER)`
   - Used to look up subscriptions without storing the phone in plaintext
   - APP_PEPPER is a random 32+ char string in `.env` (never in code)
   - Even if DB is stolen, attacker cannot brute-force E.164 space because PEPPER is unknown

2. **Ciphertext (Fernet symmetric):**
   - Stored in `phone_ciphertext` column
   - Computed: `Fernet(FERNET_KEY).encrypt(phone.encode())`
   - Only decrypted when returning the user's own phone to them in an API response
   - Same key encrypts feedback audio clips written to `data/feedback_clips/`

**Logging redaction:**
- All log lines referencing phone, email, endpoint, or coordinates use helper functions from `backend/utils/redaction.py`
- e.g., `mask_phone("+919876543210")` → `"+91***3210"`
- grep for "logger.*(phone|email)" returns no raw PII

## Authentication Flow

### User Authentication (OTP + JWT)

1. **Request OTP:**
   ```
   POST /auth/request-otp
   { "phone": "+919999999999" }
   ↓ (rate-limited to 3/hour per phone)
   ↓ Validate phone format (E.164 regex)
   ↓ Hash OTP with salt, store in auth_otps table with 5-min TTL
   ↓ Send SMS via Fast2SMS API (key from env, sent as request body, not query param)
   ← { "ok": true }
   ```

2. **Verify OTP:**
   ```
   POST /auth/verify-otp
   { "phone": "+919999999999", "otp": "123456" }
   ↓ Validate phone format
   ↓ Look up auth_otps by hash of phone
   ↓ Compare salted OTP (timing-safe comparison)
   ↓ If match: issue JWT
     └─ Header: { "alg": "HS256" }
     └─ Payload: { "sub": hash_phone(phone), "phone": phone_ciphertext, "exp": now + 24h }
     └─ Sign with JWT_SECRET (env var, HS256)
   ← { "token": "<JWT>", "expires_in": 86400 }
   ```

3. **Protected route:**
   ```
   GET /api/crop/recommend
   Authorization: Bearer <JWT>
   ↓ require_user dependency decodes JWT (verify signature + exp)
   ↓ Extract sub claim (phone_hash), store on request.state.user
   ↓ Handler proceeds; can access request.state.user.sub, etc.
   ← { "top_crop": {...}, "confidence": 0.95, ... }
   ```

### Service-to-Service Authentication (API Key)

1. **Cron/internal route:**
   ```
   GET /internal/alerts/check
   X-API-Key: <API_KEY from env>
   ↓ require_api_key dependency checks header
   ↓ Compares against settings.API_KEY (must match exactly, no default)
   ↓ Handler proceeds
   ```

## Error Handling & Resilience

- Structured errors: `ErrorResponse(code, message, detail)` — see `backend/schemas/errors.py`
- External API failures (502, timeout) log a warning and return "available: false" sentinel; never crash
- ML models wrap load in try/except; unavailable model returns 503 with `model_unavailable` code
- Caching via `cachetools.TTLCache` with per-service TTLs (weather 300s, market 900s); LRU eviction at maxsize

## Rate Limiting

Slowapi middleware: `/auth/request-otp` (3/hr/phone), `/disease/analyze` (20/hr/user), `/acoustic/analyze` (20/hr/user), `/alerts/subscribe` (5/hr/user). Excess → 429 with retry_after. See `backend/middleware/rate_limit.py`.

## Database

SQLite at `kisanos.db`. Key tables: `alert_subscriptions` (phone_hash, phone_ciphertext, crops), `webpush_subscriptions` (phone_hash, endpoint, auth), `auth_otps` (phone_hash, otp_hash, expires_at). Migrations via Alembic; run `alembic upgrade head` to initialize.

## Quick Start

Fresh contributor checklist:
1. Clone and create venv
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill env vars (API_KEY, JWT_SECRET, APP_PEPPER, FERNET_KEY)
4. `alembic upgrade head` (init DB)
5. `pytest` (verify tests pass)
6. `uvicorn backend.main:app --reload`
7. Visit `http://localhost:8000/docs` for OpenAPI explorer

For production: add HTTPS, ENV=production, JSON logging, DB backups (S3), error tracking (Sentry).
