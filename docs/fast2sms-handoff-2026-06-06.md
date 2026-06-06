# Fast2SMS Fix — HF Spaces Pipeline Handoff (2026-06-06)

Operator handoff for rolling the Fast2SMS OTP fix into the live Hugging Face
Space (private Docker Space `prajval007/smartcropadvisory`). Pairs with
`docs/deploy/huggingface.md` (the full deploy runbook).

---

## What changed (already on `main`)

- **Commit:** `8ad032d` — `fix(sms): use working Fast2SMS quick route + validate response body`
- **Files:** `backend/services/sms.py`, `tests/test_sms.py`
- `send_sms` now uses the **quick route (`route=q`)** for all messages and
  **parses the JSON `{"return": …}` body** instead of trusting the HTTP status.
- 27 auth+sms tests green locally.

## Why (root cause, confirmed by live probes 2026-06-06)

1. The original "SMS never came" was **only an invalid/expired API key**
   (`status_code 412 Invalid Authentication`) — not the code or the route.
2. Fast2SMS returns **HTTP 200 even on rejection**, so the old code (which only
   did `raise_for_status()`) logged "SMS sent" for a dead key. The new
   `return is True` check makes a real failure surface as `502 otp_send_failed`.
3. The **OTP route (`route=otp`) is LOCKED** on this account — `status_code 996`
   "complete website verification / use DLT SMS API". Do **not** switch to it
   without completing Fast2SMS verification/DLT. The **quick route works.**

Diagnostic (no SMS sent):
```bash
curl -s "https://www.fast2sms.com/dev/wallet?authorization=$FAST2SMS_API_KEY"
# healthy -> {"return":true,"wallet":"75.0000","sms_count":300}
```

---

## Pipeline steps to update the Space

### 1. Set / refresh the Space secret
**Space → Settings → Variables and secrets → Secrets** (not Variables):

- `FAST2SMS_API_KEY` = the **valid** key (the one verified working locally — the
  60-char key currently in local `.env`). The old key on the Space is the dead
  one that caused the failure; **overwrite it.**
- Confirm `ENVIRONMENT=production` is set. With a valid key + production:
  - OTP is delivered by **real SMS** (quick route), and
  - the on-screen `demo_otp` fallback is **off** (`demo_mode=False`) — production
    never leaks the code. This is the intended secure behavior.

> The key lives ONLY in the Space secret + local `.env` (gitignored). It is never
> committed — `.dockerignore` excludes `.env*`, and `.env` is in `.gitignore`.

### 2. Push the code to the Space
From `main` (already merged):
```bash
# 'space' remote per docs/deploy/huggingface.md; LFS already set up on prior deploy
git push space main
```
If this is a fresh clone, re-run the LFS + remote setup from
`docs/deploy/huggingface.md` §"Create the Space and push" first.

### 3. Verify live
- **Logs:** boot clean, uvicorn on `0.0.0.0:7860`, no missing-secret crash loop.
- **End-to-end OTP** (real SMS to a test phone):
```bash
curl -s -X POST https://<user>-<space>.hf.space/api/auth/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone":"<10-digit>"}'
# expect: {"ok":true,"phone":"+91…","demo_otp":null}   <- demo_otp MUST be null in prod
# and an SMS should arrive on the phone
```
- If `demo_otp` is non-null in production → `ENVIRONMENT` isn't `production`; fix
  the Space variable.
- If you get `502 otp_send_failed` → the key/wallet is the problem; re-run the
  wallet probe above (check balance / key validity).

### 4. Pre-demo checklist
- [ ] Wallet topped up (₹75 / 300 SMS as of 2026-06-06 — refill before demo).
- [ ] Test OTP received on a real phone via the Space URL.
- [ ] `demo_otp` is `null` in the production response.

---

## Cost note + demo login (added 2026-06-06)

The quick route is **₹5/SMS** (confirmed in the Fast2SMS transaction history:
"Quick SMS (1 SMS) → Debited ₹5.0000" per send). The cheap routes (~₹0.25/SMS)
need DLT registration / website verification, which take days — not feasible
before the demo.

**Demo login (zero cost):** set Space secret `DEMO_PHONE=1234567890`. Logging in
with that one number **skips SMS** (no ₹5 charge) and returns the OTP on screen
for instant login — works in production. Every *other* number still gets a real
SMS, and real codes are never leaked. Judges use `1234567890`; the OTP appears
on screen. Don't set it to a real user's number.

> Rate limit: `/request-otp` is **5/hour per IP**, and the `DEMO_PHONE` is
> **exempt** (unlimited) — judges can log in with `1234567890` as many times as
> they like, while real numbers stay capped at 5/hour per IP.

For a real launch later: complete **DLT registration** (TRAI DLT portal → Entity +
6-char Sender ID + approved template), then switch to `route=dlt` (~₹0.25/SMS).

## Rollback
- `git revert 8ad032d && git push space main`, or
- Space UI → **Settings → Factory rebuild** / pin a previous commit.

## Constraints / gotchas
- **Do not** re-enable `route=otp` until Fast2SMS website verification/DLT is done.
- The SQLite DB is ephemeral on HF — OTP records reset on restart/sleep (fine; OTPs
  are short-lived anyway).
- Quick-route SMS is non-DLT promotional; carriers may apply DND filtering. For a
  production launch (not demo), complete DLT and switch to a DLT template route.

See memory: `project_fast2sms`, `project_hf_deploy`.
