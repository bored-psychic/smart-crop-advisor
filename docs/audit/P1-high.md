# P1 — High Severity Remediation (Smart Crop Advisor)

> **For the executing sub-agent**: Self-contained brief. Read fully before
> acting. Each task lists its `Scope` so you know your boundary. Stop when
> your task's verification passes and report back. **Do not modify files
> outside your Scope.**

## Status (as of 2026-05-22)

**P0 is fully landed** — all seven shipping-blockers closed. You can trust
that:

| P0 Task | Commit | What it gave you |
|---|---|---|
| 1. Secrets/.env hygiene | `1ff0388` | `.env.example` has all required placeholders |
| 2. Drop dev-key fallback | `2799e8d` | `API_KEY` + `JWT_SECRET` are required env vars |
| 3. OTP+JWT auth | `7d5ba4f` | `backend/auth.py` exports `require_user`, `require_api_key`, `issue_token`, `hash_phone` |
| 4. CORS tighten | `5775345` | `CORS_ORIGINS` explicit, no wildcard |
| 5. Rate limits | `dd0ceb4` | `slowapi` wired; `backend/middleware/rate_limit.py:limiter` available |
| 6. `/alerts/history` JWT-scoped | `c381977` | Phone derived from JWT, not query param |
| 7. Real Login.jsx | `7d5ba4f` (bundled) | OTP→JWT flow works end-to-end |

**P1 tasks already completed**:

- ✅ **Task 8 (Real frontend Login)** — landed in `7d5ba4f`. `Login.jsx`
  calls `/auth/request-otp` + `/auth/verify-otp`, stores JWT in
  `localStorage`. Smoke-tested 2026-05-22.
- ✅ **Task 9 (Roll out `require_user`)** — landed. `backend/auth.py` now
  exports `require_user_or_api_key`. Routers:
  - **Dual-mode** (`require_user_or_api_key`): `crop`, `market`,
    `irrigation`, `field_watch` (Streamlit also hits these).
  - **Pure `require_user`**: `soil`, `dosage`, `disease`, `acoustic`,
    `alerts`.
  - `tests/conftest.py` exposes `auth_token` and `auth_headers` session
    fixtures. Use them in new tests.

**Defaults locked in (easy to flip later)**: OTP+JWT/HS256, 24h TTL,
`localStorage` token storage.

**Known test failures rolled into P1** (do NOT fix them outside their
owning task):

| Failing test | Owning task |
|---|---|
| `test_bundles_schema` (missing i18n keys: Subscribe, Frost Warning, …) | **Task 6** — backfill router/i18n tests; add missing bundle keys as part of that pass |
| `test_yamnet_model` ×2 (network fetch of model weights) | **Task 6** — mock the fetch |
| `test_soil_analysis` (collection error) | **Task 6** — investigate missing fixture/import |

## Project context

FastAPI backend + React (`web/`) + Streamlit (`frontend/`) + SQLite at
`/Users/kiyo/smart-crop-advisor`. The P1 items are about **reliability,
correctness, abuse prevention, and unblocking future work**. Recurring
patterns: bare `except` swallowing real failures, an unbounded in-memory
cache, plaintext PII at rest, missing validation, missing tests, and four
orphaned modules that confuse anyone reading the code.

## Dispatch order

Execute in this order. Tasks within the same wave can run in parallel
(disjoint scopes); waves are sequenced.

**Wave A — parallel, no inter-task dependencies**

- Task 1 — silent error swallowing
- Task 2 — bounded cache
- Task 3 — PII encryption at rest
- Task 4 — SMS key transport + PII logging
- Task 5 — input validation
- Task 7 — delete dead modules

**Wave B — after Wave A is green**

- Task 6 — backfill router tests (depends on stabilized routers from
  Waves A + the validation schemas from Task 5; also rolls in the three
  known failing tests above)

**Dispatch template** (one sub-agent per task):

> "Execute Task N of `/Users/kiyo/smart-crop-advisor/docs/audit/P1-high.md`.
> Read the whole file for context, then implement only Task N. Do not
> modify files outside Task N's Scope block. Run the Verification block
> and report results."

---

## Task 1 — Replace silent error swallowing in external HTTP calls

**Scope**: `backend/services/field_watch.py`, `backend/services/market.py`,
`backend/services/weather.py` (only if still present after Task 7),
`backend/services/market_service.py`, `backend/services/weather_service.py`,
`backend/routers/disease.py`, `backend/routers/acoustic.py`,
`backend/services/firms_service.py`.

**Steps**:

1. `backend/services/field_watch.py:51` — bare `except Exception: pass`
   wraps weather/fire/locust API calls. Replace with per-source
   `try/except` blocks that log at `WARNING` (use `logger.exception`) and
   return a typed "unavailable" sentinel, not silent zeros.
2. Anywhere `requests.get(...).json()` or `httpx.get(...).json()` appears
   without a status check (confirmed: `market.py:43`, `weather.py:18`,
   `field_watch.py:23,42,89,114`), add `resp.raise_for_status()` first.
3. `backend/routers/disease.py:86` and `backend/routers/acoustic.py:530`:
   `resp.content[0].text` will `IndexError` if Anthropic returns no
   content blocks. Guard with
   `if not resp.content: raise HTTPException(503, ...)`.
4. Replace bare `except:` and `except Exception: pass` everywhere with
   either (a) a typed `except (httpx.HTTPError, json.JSONDecodeError)`
   that logs, or (b) intentional re-raise. No silent catches.

**Verification**:

- Add `tests/test_external_resilience.py` that uses `respx` to simulate
  502s and timeouts from OWM and Agmarknet, asserts the field-watch
  endpoint returns 200 with `"weather": {"available": false}` (or similar)
  and logs a warning. Use the `auth_headers` fixture from `conftest.py`.
- `grep -RE "except[^:]*:\s*pass" backend/` returns nothing.

---

## Task 2 — Bound the in-memory cache

**Scope**: `backend/core/cache.py`, callers.

**Steps**:

1. `backend/core/cache.py:9,62` — replace the unbounded global dict with
   `cachetools.TTLCache(maxsize=10_000, ttl=<configured>)`. Add
   `cachetools` to `requirements.txt` (pinned).
2. Preserve the existing public API (`get`, `set`, etc.). Don't break
   callers.
3. If the cache key space is per-endpoint (market quotes vs weather vs
   i18n dynamic), use a `TTLCache` *per namespace* keyed by a string
   prefix — simpler eviction and clearer metrics.

**Verification**:

- New unit test: insert 10_001 distinct keys, assert size stays ≤
  `maxsize`.
- Manual soak: run `ab -n 5000 -c 50 http://localhost:8000/<cached route>`
  and observe RSS plateau in `ps -o rss=`. Document the before/after.

---

## Task 3 — Encrypt PII at rest

**Scope**: `backend/services/db.py`, `backend/routers/subscriptions.py`,
`backend/routers/acoustic.py`, `data/feedback_clips/`.

**Steps**:

1. Phones in `alert_subscriptions.phone` and `webpush_subscriptions.phone`:
   store a `phone_hash = sha256(phone + APP_PEPPER)` for lookups and a
   `phone_ciphertext` (Fernet symmetric, key in env) for decrypt-on-read.
   Migrate existing rows in a one-off script (`scripts/migrate_pii.py`)
   and document in `docs/audit/`.
2. Feedback audio clips written to `data/feedback_clips/` in
   `acoustic.py:81-90`: either (a) encrypt with the same Fernet key
   before `out.write_bytes`, or (b) move to object storage (S3/R2) with
   server-side encryption. Pick (a) for now; (b) is a separate effort.
3. Add `APP_PEPPER` and `FERNET_KEY` to `.env.example` and
   `backend/config.py` as required env vars.

**Note**: `backend/auth.py:hash_phone()` already does
`sha256(phone)` without a pepper — that's the JWT subject. Don't reuse
it for the DB lookup hash; add a separate peppered variant.

**Verification**:

- `sqlite3 kisanos.db "SELECT phone FROM alert_subscriptions LIMIT 1"`
  returns ciphertext, not a `+91...` string.
- `ls data/feedback_clips/` files do not play in `ffplay` without decrypt.
- Round-trip test: subscribe with a phone, fetch history with a JWT
  minted via `backend.auth.issue_token`, see the phone decrypted
  correctly in the response.

---

## Task 4 — Fix SMS API key transport and PII logging

**Scope**: `backend/services/sms.py`.

**Steps**:

1. `sms.py:22` — Fast2SMS key is sent as a query param. Check Fast2SMS
   docs; if they accept the key as a header, switch. If not, ensure your
   reverse proxy access logs strip query strings, or move the key into the
   request body as JSON.
2. `sms.py:11,28` — `logger.info(f"[SMS STUB] To: {phone} | {message}")`
   and `logger.info(f"SMS sent to {phone}: {resp.text}")` log raw PII.
   Replace `phone` with `phone[:3] + "***" + phone[-2:]` in log lines and
   drop `resp.text` (log the status code only).

**Verification**:

- `grep -n "logger.*phone" backend/services/sms.py` shows no raw phone
  values in format strings.
- Send a test SMS in dev, check stdout — should show masked phone.

---

## Task 5 — Validate inputs

**Scope**: `backend/schemas/subscriptions.py`,
`backend/routers/acoustic.py`, `backend/routers/disease.py`.

**Steps**:

1. `subscriptions.py:7-10` — change `phone: str` to
   `phone: Annotated[str, Field(pattern=r"^\+?[1-9]\d{7,14}$")]`. Change
   `crops: list[str]` to
   `Annotated[list[Literal[<known crops>]], Field(max_length=20)]`. Pull
   the literal list from `core/disease_db.py` or a dedicated constants
   module.
2. `acoustic.py:121` — `dest_dir = AUDIO_SAMPLES_DIR / label.replace(...)`.
   Replace with an allowlist: load known label slugs from the labels
   file used by training, reject anything not in the set with 400.
3. `disease.py:96` — `crop_type: str = Form("Unknown")`. Change to a
   `Literal` of supported crops; reject otherwise.

**Verification**:

- New tests in `tests/test_validation.py`: posting `phone="; DROP"`,
  `label="../../etc"`, `crop_type="<script>"` returns 422. Use the
  `auth_headers` fixture.

---

## Task 6 — Backfill router tests + fix the three known failures

**Scope**: `tests/` only. Touch nothing outside `tests/` except the i18n
bundle JSON files needed to satisfy `test_bundles_schema`.

**Run AFTER** Wave A is merged — Task 5's validators and Task 1's typed
exception handlers change the response shapes these tests will pin.

**Five missing router tests**:

1. `tests/test_market_router.py` — happy path for
   `GET /market/prices/<state>/<crop>`, plus 503 when Agmarknet times out
   (mocked).
2. `tests/test_field_watch_router.py` — assert partial response when
   weather/fire/locust each individually fail.
3. `tests/test_irrigation_router.py` — happy path + missing crop returns
   422.
4. `tests/test_crop_router.py` — recommendation endpoint with valid soil
   inputs returns top-N; invalid pH returns 422.
5. `tests/test_subscriptions_router.py` — subscribe, list, unsubscribe;
   plus the JWT auth gate from P0 Task 6.

All five use the `auth_headers` fixture from `tests/conftest.py`. Mock
external HTTP with `respx`.

**Three pre-existing failures to clear** (rolled into this task):

- `test_bundles_schema` — i18n bundles are missing keys (`Subscribe`,
  `Frost Warning`, others). Either add the keys to every bundle in
  `web/lib/bundles/*.json` (preferred) **or** mark the offending keys as
  intentionally optional in the schema if they're truly dynamic. Run the
  bundle linter (`scripts/i18n_lint.py` or similar) to confirm.
- `test_yamnet_model` ×2 — currently downloads model weights at test
  time. Mock the URL fetch (`respx` or `monkeypatch` the loader) so the
  tests run offline.
- `test_soil_analysis` (collection error) — likely a missing fixture or
  bad import after recent refactors. Investigate, fix the import, or
  delete the test if the underlying code is gone.

**Verification**:

- `pytest` from the repo root: **all** tests green (was 119/123, target
  is 123/123 after this task).
- `pytest --cov=backend.routers` — coverage of `backend/routers/` ≥ 70 %.

---

## Task 7 — Delete confirmed dead modules

**Scope**: precise file deletions only. Do NOT refactor live code.

**Files to delete**:

- `/Users/kiyo/smart-crop-advisor/services/soil.py` (root)
- `/Users/kiyo/smart-crop-advisor/backend/services/market.py`
- `/Users/kiyo/smart-crop-advisor/backend/services/weather.py`
- `/Users/kiyo/smart-crop-advisor/backend/services/soil.py`
- `/Users/kiyo/smart-crop-advisor/backend/core/config.py`

**Before deleting each**:

1. `grep -RE "from (\.\.|backend|services)\.\w+ import" backend/ frontend/ web/ tests/ scripts/`
   and confirm zero imports of the target module.
2. Diff the dead module against its live sibling
   (`backend/services/market_service.py`, etc.) to confirm no unique
   logic has been orphaned. If you find unique logic, lift it into the
   live sibling first, then delete.
3. After all five deletes, run `pytest` — it should pass without further
   change.

**Verification**:

- `git rm` lands cleanly.
- `pytest` green.
- `python -c "import backend.main"` boots without import errors.

---

## Out of scope (P2 / P3)

- God-file split for `acoustic.py` (P2).
- Alembic / DB migrations framework (P2).
- Security headers, `requirements.txt` pinning, i18n fallback (P2/P3).
- Dependency reduction across TF + Torch + librosa (P3).
- Switch JWT to `httpOnly` cookies + refresh tokens (separate follow-up).

## Done criteria

- All seven remaining verification blocks pass.
- `pytest` 123/123 green; `pytest --cov=backend` baseline maintained.
- No bare `except:` left in `backend/`.
- No raw phone numbers in DB rows or logs.
- Five dead modules gone.
- Bounded cache enforced under load.
