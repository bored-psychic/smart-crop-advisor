# P0 — Critical Remediation (Smart Crop Advisor)

> **For the executing sub-agent**: This file is your complete brief. You do
> not have prior conversation context. Read this file in full before doing
> anything. Each task is an independent unit; complete them in the listed
> order because later tasks depend on earlier ones. Do not work outside the
> file paths listed in *Scope*. When all tasks pass their verification step,
> stop and report back.

## Project context

Smart Crop Advisor: FastAPI backend (`backend/`) + React (`web/`) + Streamlit
(`frontend/`) + SQLite. Repo root is `/Users/kiyo/smart-crop-advisor`. App
entrypoint is `backend/main.py`; web config at `web/config.js`; secrets in
`.env`. The three P0 problems together mean **anyone reading the repo or
opening DevTools currently has full backend access**. Fix in the listed order
— rotating secrets before deauthorizing the hardcoded default would lock
yourself out; restricting CORS before fixing auth would brick the frontend.

## Scope (files you may modify)

- `.env`, `.env.example`, `.gitignore`
- `backend/config.py`, `backend/main.py`, `backend/auth.py`
- `backend/routers/subscriptions.py`, `backend/routers/disease.py`,
  `backend/routers/acoustic.py`
- `web/config.js`, `web/components/app.jsx`, `web/components/Login.jsx`,
  `web/lib/api.js`
- New file: `backend/middleware/rate_limit.py` (or equivalent)
- `requirements.txt` (only to add `slowapi`)
- `tests/` (add coverage for changes)

Do **not** touch ML code, i18n, or routers outside the list above.

---

## Task 1 — Purge committed secrets and rotate keys

**Why**: `.env` contains live Anthropic, Gemini, OpenWeatherMap, Fast2SMS, and
VAPID keys, and is in the git history. They must be rotated *and* removed
from history.

**Steps**:

1. Inventory: open `.env` and list every key. For each one, generate a new
   value from the provider console (Anthropic dashboard, Google AI Studio,
   openweathermap.org, fast2sms.com, generate new VAPID pair via
   `py-vapid` or `web-push`). **Confirm with the user before rotating** —
   rotation invalidates prod traffic.
2. Add `.env` to `.gitignore` if not already; create `.env.example` with
   placeholder values and the variable names only.
3. Use `git filter-repo --path .env --invert-paths` to scrub `.env` from
   history. If `git filter-repo` isn't installed, fall back to
   `git filter-branch` (slower but bundled).
4. Force-push the rewritten history. **Coordinate with the user first** —
   collaborators must re-clone.
5. Write the new keys into a local `.env` only.

**Verification**:
- `git log --all --full-history -- .env` returns nothing.
- `grep -R "sk-ant-" .` and similar prefix searches return no committed code.
- Backend boots locally with the new `.env`.

---

## Task 2 — Remove hardcoded API key defaults

**Why**: `backend/config.py:22` defaults `API_KEY` to
`"kisanos-dev-key-change-in-production"`, and `backend/main.py:25` compares
against it. If the env var is unset, auth silently disables.

**Steps**:

1. In `backend/config.py`, change `API_KEY: str = "kisanos-dev-..."` to a
   required field (`API_KEY: str` with no default, or Pydantic
   `Field(..., env="API_KEY")`). Pydantic-settings will raise
   `ValidationError` on missing env at boot — that's the desired behavior.
2. Delete the startup warning in `backend/main.py:31-43` that announces use
   of the default key.
3. Audit `backend/auth.py:13-30`: ensure the comparison uses the loaded
   setting, not a literal string.
4. In `backend/main.py`, wrap the settings load in a clear error message:
   `"API_KEY env var is required"`.

**Verification**:
- `unset API_KEY && python -c "from backend.config import get_settings; get_settings()"` raises.
- With `API_KEY=test-key`, `curl http://localhost:8000/health` succeeds;
  `curl -H "X-API-Key: wrong" ...` returns 401.

---

## Task 3 — Replace browser-side API key with per-user auth

**Why**: `web/config.js:1` ships the API key to every visitor. Anyone with
DevTools is your backend. The current `localStorage.kisan.auth = "1"` flag
in `web/components/app.jsx:26` is not auth.

**Decision needed from user before proceeding**: which auth model?
(a) phone + OTP via existing Fast2SMS pipeline → JWT, or
(b) email + password via a hosted auth provider (Clerk/Supabase Auth/Auth0).
**Ask via AskUserQuestion before implementing.**

**Steps (assuming OTP/JWT — adjust if user picks (b))**:

1. Add `POST /auth/request-otp { phone }` → triggers Fast2SMS, stores
   hashed OTP in SQLite with 5-min TTL.
2. Add `POST /auth/verify-otp { phone, otp }` → on match, returns a signed
   JWT (HS256, secret from env, 24h TTL) containing `sub=phone_hash`.
3. Replace `require_api_key` dependency in `backend/auth.py` with
   `require_user`, which validates the JWT from `Authorization: Bearer`
   header. Keep `require_api_key` available only for service-to-service
   routes (clearly documented).
4. In `web/lib/api.js`, attach `Authorization: Bearer <token>` from
   `localStorage` (or sessionStorage). Remove `window.API_KEY` usage.
5. In `web/components/Login.jsx`, replace `setTimeout(..., 480)` with real
   OTP request/verify flow.
6. In `web/components/app.jsx`, replace `kisan.auth === '1'` with a token
   presence + JWT-decode check (use `jwt-decode`).
7. Delete `web/config.js`'s `window.API_KEY = "..."` line. Keep the file for
   non-secret config (e.g., `API_BASE_URL`).

**Verification**:
- DevTools network tab shows `Authorization: Bearer ...`, no `X-API-Key`.
- DevTools application tab shows JWT, not `kisan.auth: 1`.
- `curl` against a protected route with an expired/forged JWT returns 401.

---

## Task 4 — Restrict CORS

**Why**: `backend/main.py:138-144` has `allow_origins=["*"]`,
`allow_methods=["*"]`, `allow_headers=["*"]`. Once auth lives in tokens
(Task 3), CORS still needs to be tightened.

**Steps**:

1. In `backend/config.py`, change `CORS_ORIGINS` default to `[]` and require
   the env var (or default to `["http://localhost:5173"]` for dev).
2. Make `backend/main.py` read the list from settings; do not fall back to
   `["*"]` if empty.
3. Set `allow_credentials=False` unless the frontend needs cookies (it
   shouldn't with JWT in Authorization header).
4. Restrict `allow_methods` to `["GET", "POST"]` and `allow_headers` to
   `["Authorization", "Content-Type"]`.

**Verification**:
- Preflight from a disallowed origin returns 400/no CORS headers.
- Preflight from the allowed origin returns 204 with correct
  `Access-Control-Allow-Origin`.

---

## Task 5 — Rate limit expensive endpoints

**Why**: `/alerts/subscribe` triggers paid SMS; `/disease/analyze` runs
Claude Vision on 10 MB uploads; `/acoustic/analyze` fans out to PANNs +
YAMNet + Gemini + Claude. None has a per-IP or per-user limit.

**Steps**:

1. Add `slowapi==0.1.9` (or current pinned) to `requirements.txt`.
2. Create `backend/middleware/rate_limit.py` exporting a `slowapi.Limiter`
   keyed on `get_remote_address` *or* the authenticated user (preferred,
   once Task 3 lands). Wire the limiter into `backend/main.py` via the
   documented `slowapi` setup.
3. Apply decorators:
   - `subscriptions.py` `/alerts/subscribe` — `@limiter.limit("5/hour")`.
   - `disease.py` `/disease/analyze` — `@limiter.limit("20/hour")`.
   - `acoustic.py` `/acoustic/analyze` — `@limiter.limit("20/hour")`.
   - `subscriptions.py` `/auth/request-otp` (from Task 3) —
     `@limiter.limit("3/hour")` keyed on the submitted phone.
4. Return clear 429 JSON: `{"error": "rate_limited", "retry_after": <s>}`.

**Verification**:
- `for i in $(seq 1 6); do curl ...; done` against `/alerts/subscribe`
  returns 429 on the 6th call within the hour.
- Test: add `tests/test_rate_limit.py` exercising one limited route.

---

## Task 6 — Lock down `/alerts/history`

**Why**: `backend/routers/subscriptions.py:57` takes `phone` as a query
param with no proof the caller owns that phone.

**Steps**:

1. Once Task 3 is in, change the endpoint to read the phone from the JWT
   (`request.state.user.phone_hash`), not the query string.
2. Reject requests with no token via `require_user`.
3. Update the React caller in `web/components/views/` (find the right
   view) to drop the `phone` param.

**Verification**:
- `curl ".../alerts/history?phone=+919999999999"` without a token → 401.
- With a token for a *different* phone → 403 or empty result.
- With the matching token → returns this user's history only.

---

## Task 7 — Replace `localStorage.kisan.auth = '1'`

**Why**: `web/components/app.jsx:26,44,116,125` uses a literal `"1"` flag.
Already addressed by Task 3, but verify all four sites are removed.

**Steps**:

1. `grep -n "kisan.auth" web/` — every match must be deleted or replaced
   with a JWT presence check.
2. The "logged in" gate should be: token present *and* not expired (decode
   `exp` claim).
3. Logout should both clear the token and call a backend `/auth/logout`
   endpoint that revokes (if you maintain a denylist) or simply does
   nothing if JWTs are stateless.

**Verification**:
- `grep -n "kisan.auth" web/` returns nothing.
- Setting a fake token (`localStorage.setItem('token','garbage')`) and
  reloading does not grant access; the app routes to Login.

---

## Out of scope (do not attempt in this PR)

- ML/feature work, i18n changes, dead-code purges, cache rewrites, DB
  migrations, PII-at-rest encryption — those live in P1.
- Switching auth provider beyond what user picks in Task 3.
- Streamlit (`frontend/`) auth — gate that separately.

## Done criteria

All seven verification blocks pass, plus:
- `pytest tests/` is green.
- A clean clone + fresh `.env` (from `.env.example`) + `pip install` + boot
  succeeds.
- One reviewer can read the diff in under 30 minutes and confirm each task
  was implemented as written.
