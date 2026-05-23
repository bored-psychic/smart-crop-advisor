# P2 — Medium Severity Remediation (Smart Crop Advisor)

> **For the executing sub-agent**: Self-contained brief. Read fully before
> acting. Tasks here are independent; safe to parallelize one sub-agent per
> task. Do P0 and P1 first — several P2 tasks assume new auth, validated
> inputs, and bounded caches are already in place.

## Project context

These are correctness, performance, and hygiene fixes that aren't
shipping-blockers but will bite within the first 100 users: deprecated
async APIs, silent schema migrations, no DB indexes on hot columns, a
1399-line god file in the acoustic router, missing security headers, raw
i18n key leakage, and PII in logs.

---

## Task 1 — Replace deprecated `get_event_loop().run_in_executor`

**Scope**: `backend/services/market.py:9`, `backend/services/weather.py:8`
(if still present), any other usages found via
`grep -RE "get_event_loop\(\)\.run_in_executor" backend/`.

**Steps**:

1. Replace with `await asyncio.to_thread(blocking_fn, *args)` (Python 3.9+).
2. Remove now-unused `loop` variables.

**Verification**:
- `grep -RE "get_event_loop" backend/` returns nothing.
- `pytest` green.

---

## Task 2 — Adopt Alembic; index hot columns

**Scope**: new `alembic/` directory, `backend/services/db.py`,
`requirements.txt`.

**Steps**:

1. Install Alembic; run `alembic init alembic`; configure
   `sqlalchemy.url` to read from `backend.config`.
2. Generate an initial revision that reflects the current schema in
   `db.py:9-19` (don't rely on `--autogenerate` for SQLite from raw SQL;
   write the upgrade by hand).
3. Add a second revision creating indexes:
   `CREATE INDEX idx_alert_subscriptions_phone ON alert_subscriptions(phone_hash);`
   `CREATE INDEX idx_webpush_subscriptions_phone ON webpush_subscriptions(phone_hash);`
   (Use `phone_hash` from P1 Task 3; if P1 not landed, use `phone` and
   plan a follow-up index.)
4. Remove the silent `ALTER TABLE ADD COLUMN preferred_lang` migration in
   `db.py:40-46`; that's now Alembic's job.
5. Document the upgrade path in `docs/audit/migrations.md`: `alembic upgrade head`.

**Verification**:
- Fresh checkout: `alembic upgrade head` produces the schema; `pytest`
  green.
- `EXPLAIN QUERY PLAN SELECT * FROM alert_subscriptions WHERE phone_hash=?`
  in sqlite3 shows `USING INDEX`.

---

## Task 3 — i18n fallback should not return the raw key

**Scope**: `backend/services/i18n/catalog.py`.

**Steps**:

1. `catalog.py:54-58` — current behavior returns the lookup key when both
   target and English are missing. Change to return a placeholder
   (configurable; default `"???"`) *and* `logger.warning("i18n miss: lang=%s key=%s", lang, key)`.
2. Add a `strict` mode (env var `I18N_STRICT=1`) that raises in
   development so missing keys are caught in tests rather than shipped.

**Verification**:
- Test: `t("nonexistent.key", "fr")` returns `"???"`, not
  `"nonexistent.key"`.
- With `I18N_STRICT=1`, the same call raises.

---

## Task 4 — Add security headers

**Scope**: `backend/main.py`, new
`backend/middleware/security_headers.py`.

**Steps**:

1. Create a Starlette middleware that sets, on every response:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
     (only when `request.url.scheme == "https"`)
   - `Content-Security-Policy:` reasonable default; start with
     `default-src 'self'; img-src 'self' data:; connect-src 'self' <api host>; script-src 'self'`
     and tighten after testing the React app.
2. Wire into `backend/main.py` after CORS middleware.

**Verification**:
- `curl -I http://localhost:8000/health` shows the headers.
- React app still loads (CSP didn't break the bundle).

---

## Task 5 — Split the acoustic router

**Scope**: `backend/routers/acoustic.py` (currently 1399 lines), new
modules in `backend/services/acoustic/`.

**Steps**:

1. Create `backend/services/acoustic/__init__.py`,
   `pipeline.py`, `cache.py`, `ml.py`, `dsp.py`.
2. Move out of `acoustic.py`:
   - `dsp.py`: `_normalize_lufs` (210-232), `_snr_and_onsets` (245-315),
     `_band_energies` (316-331), `_spectrogram_png` (332-366).
   - `cache.py`: `_RESPONSE_CACHE` and its accessors (53-76); switch to
     `cachetools.LRUCache(maxsize=64)`.
   - `ml.py`: Claude/Gemini fan-out (~381-810), model selection logic.
   - `pipeline.py`: orchestration (load → normalize → DSP → ML → cache).
3. `acoustic.py` becomes routes only; each endpoint calls
   `pipeline.analyze(...)`. Target ≤ 300 lines.

**Verification**:
- `wc -l backend/routers/acoustic.py` shows ≤ 300.
- `pytest tests/test_panns_model.py tests/test_yamnet_model.py` and the
  acoustic router contract test from P1 all green.
- Manual: hit `/acoustic/analyze` with a sample WAV and confirm the
  response shape is unchanged.

---

## Task 6 — Gate `/vapid-public-key`

**Scope**: `backend/routers/subscriptions.py:85-90`.

**Steps**:

1. Add `dependencies=[Depends(require_user)]` (or `require_api_key` for
   the Streamlit client) to the endpoint.
2. If a public unauthenticated push setup must work for unsigned visitors,
   leave as-is and instead document the threat model in code.

**Verification**:
- `curl .../vapid-public-key` without token → 401.

---

## Task 7 — Redact PII from logs everywhere

**Scope**: `backend/services/sms.py`, `backend/services/webpush_service.py`,
plus any `logger.info/debug` call referencing `phone`, `email`,
`endpoint`, or coords. Find with
`grep -REn "logger\.(info|debug).*(phone|email|endpoint|lat|lon)" backend/`.

**Steps**:

1. Add a `backend/utils/redaction.py` with `mask_phone(p)`,
   `mask_endpoint(url)`, `mask_coord(c)`.
2. Replace inline f-strings with the helpers.
3. Add a unit test ensuring `mask_phone("+919876543210") == "+91***3210"`.

**Verification**:
- Re-run the `grep` above; every match uses a redaction helper or is a
  WARN/ERROR with explicit allow.

---

## Task 8 — Graceful ML degradation

**Scope**: `backend/ml/panns_model.py:36`, `backend/ml/yamnet_model.py`,
`backend/routers/acoustic.py` startup.

**Steps**:

1. On boot (FastAPI `startup` event), try to load each ML head; if a file
   is missing, log an ERROR and set a module flag
   `MODEL_AVAILABLE = False`.
2. In the acoustic pipeline, if the relevant model is unavailable, skip
   it and either (a) fall back to the next available model or (b) return
   a 503 with a clear `model_unavailable` payload, depending on which
   model failed.
3. Document the dependency map in `docs/audit/ml-fallbacks.md`.

**Verification**:
- Move `backend/models/panns_head.joblib` to `.bak`, boot the app, hit
  `/acoustic/analyze`. The response should be a structured 503, not an
  unhandled exception.

---

## Task 9 — Unify error response shape

**Scope**: every router; new `backend/schemas/errors.py`.

**Steps**:

1. Define `ErrorResponse(code: str, message: str, detail: dict | None)`.
2. Add an exception handler in `backend/main.py` that converts
   `HTTPException` to this shape.
3. Update all `raise HTTPException(...)` call sites to pass a `code`
   (e.g., `"crop_not_found"`, `"model_unavailable"`) via a small helper.

**Verification**:
- `curl ... /crop/nonexistent` returns JSON matching `ErrorResponse`.
- Frontend `ViewCrop.jsx` (and siblings) display `message` not raw text.

---

## Out of scope

- Requirements pinning, ML stack reduction, Streamlit refactor (P3).
- Postgres migration, multi-tenant — separate effort.

## Done criteria

- All nine verification blocks pass.
- `pytest --cov=backend` ≥ 80 % on routers, ≥ 70 % overall.
- `wc -l backend/routers/acoustic.py` ≤ 300.
- `curl -I` shows all four security headers.
- Logs from a 1-hour soak contain no raw phones, emails, or push
  endpoints.
