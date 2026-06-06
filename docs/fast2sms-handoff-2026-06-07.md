# OTP / Fast2SMS — Session Handoff (2026-06-07)

Full state of the phone-OTP auth + Fast2SMS work after this session. Supersedes
`docs/fast2sms-handoff-2026-06-06.md` (still valid, narrower scope). Pairs with
`docs/deploy/huggingface.md` for the deploy mechanics.

---

## TL;DR — what to do to ship

1. On the HF Space (`prajval007/smartcropadvisory`), set Secrets:
   - `FAST2SMS_API_KEY` = the **valid** key (overwrite the old dead one).
   - `DEMO_PHONE` = `1234567890`
   - keep `ENVIRONMENT=production`.
2. Push code: `git push origin main` then `git push space main`.
3. Verify: judges log in with **`1234567890`** → OTP shows on screen, no SMS,
   unlimited. Real numbers → real SMS, 5/hour per IP.

`main` has **4 unpushed commits** (see below) — nothing is live until pushed.

---

## How OTP delivery works now

`POST /api/auth/request-otp` has three paths:

| Condition | SMS sent? | OTP on screen (`demo_otp`)? | Rate limit |
|---|---|---|---|
| phone == `DEMO_PHONE` | ❌ no (saves ₹5) | ✅ yes (even in prod) | **exempt / unlimited** |
| real number, key set | ✅ via quick route | ❌ no | 5/hour per IP |
| dev fallback (no key, non-prod) | ❌ stub logs it | ✅ yes | 5/hour per IP |

- Real codes are **never** leaked in production for non-demo numbers.
- Frontend already reads `demo_otp` and displays it — no frontend change needed.

## Root-cause history (so nobody re-litigates it)

- "SMS never came" was caused **only by an invalid/expired API key** (`412
  Invalid Authentication`) — not the code or route.
- Fast2SMS returns **HTTP 200 even on failure**; `send_sms` now parses the JSON
  `return` field so a rejected send fails loudly (`502 otp_send_failed`) instead
  of silently logging "sent".
- **OTP route (`route=otp`) is LOCKED** on this account — `status_code 996`,
  needs website verification / DLT. **Do not use it.** The code uses the
  **quick route (`route=q`)**, which works.

## Cost reality

- Quick route = **₹5.00 / SMS** (confirmed in Fast2SMS transaction history).
- Wallet was ₹75 / ~₹70 after testing — **top up before the demo**.
- Cheap routes (~₹0.25/SMS) need **DLT registration** (TRAI DLT portal → Entity
  ID + 6-char Sender ID + approved content template; days to ~2 weeks). Only
  worth it for a real launch, not the demo. The `DEMO_PHONE` is the demo answer.

## Rate limiting

- `/request-otp`: **5/hour per IP** (was 3). Keyed per-IP, not per-phone, so
  cycling numbers doesn't dodge it.
- `DEMO_PHONE` is **exempt**: `_otp_phone_dep` (a FastAPI dep) stashes the
  normalised phone on `request.state` before slowapi fires, and
  `_otp_rate_limit_key` returns `""` for the demo number → slowapi skips the
  limit. See `backend/middleware/rate_limit.py`.

---

## Commits on `main` from this session (unpushed)

| SHA | What |
|---|---|
| `8ad032d` | fix(sms): quick route + validate Fast2SMS JSON response |
| `299ac48` | docs: Fast2SMS HF pipeline handoff (2026-06-06) |
| `9ebc86a` | feat(auth): DEMO_PHONE skips SMS + shows OTP on screen |
| `777a599` | feat(auth): exempt DEMO_PHONE from rate limit; cap 5/hour |

Files touched: `backend/services/sms.py`, `backend/routers/auth.py`,
`backend/config.py`, `backend/middleware/rate_limit.py`, `.env.example`,
`tests/test_sms.py`, `tests/test_auth.py`, `tests/test_rate_limit.py`.

## Tests — 39 passing

`pytest tests/test_auth.py tests/test_sms.py tests/test_rate_limit.py`

Covers: demo number shows OTP + sends 0 SMS, demo number unlimited (8 calls no
429), real number's 6th call 429, Fast2SMS rejection → `send_sms` returns False,
key function exempts demo / IP-buckets the rest, prod never leaks real codes.

## Verify live (after push + secrets)

```bash
# wallet (no SMS sent)
curl -s "https://www.fast2sms.com/dev/wallet?authorization=$FAST2SMS_API_KEY"
# -> {"return":true,"wallet":"…","sms_count":…}

# demo login on the Space — demo_otp present, no SMS
curl -s -X POST https://<user>-<space>.hf.space/api/auth/request-otp \
  -H "Content-Type: application/json" -d '{"phone":"1234567890"}'
# -> {"ok":true,"phone":"+911234567890","demo_otp":"……"}

# real number — demo_otp MUST be null (no leak), and an SMS should arrive
curl -s -X POST https://<user>-<space>.hf.space/api/auth/request-otp \
  -H "Content-Type: application/json" -d '{"phone":"<your-10-digit>"}'
# -> {"ok":true,"phone":"+91…","demo_otp":null}
```

## Caveats / future

- **DLT registration** is the only path to cheap (~₹0.25) compliant SMS at scale.
  Until then, real-number SMS costs ₹5 each.
- HF SQLite is ephemeral — OTP rows reset on restart/sleep (fine; OTPs expire in
  5 min anyway).
- `DEMO_PHONE` must never be set to a real user's number (anyone can log into it).

Memory: `project_fast2sms`, `project_hf_deploy`.
