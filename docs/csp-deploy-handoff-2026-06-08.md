# CSP Hardening + HF Deploy — Session Handoff (2026-06-08)

Full state of the production CSP-hardening work and the live Hugging Face deploy.
Pairs with `docs/deploy/huggingface.md` (deploy mechanics) and
`docs/fast2sms-handoff-2026-06-07.md` (auth). Memory: `project_hf_deploy`.

---

## TL;DR — where things stand

- **Live Space:** `https://prajval007-smartcropadvisory.hf.space` — now **PUBLIC**,
  Docker SDK, sha **`86cb5358`** (= local branch `deploy-snap5`).
- **CSP hardening is DONE in code and DEPLOYED.** Production serves a precompiled,
  Babel-free frontend under a strict CSP (`script-src 'self'`, no
  `unsafe-eval`/`unsafe-inline`/unpkg).
- **2 open items:**
  1. **Verify the live render** of `deploy-snap5` (the MIME fix) — the prior build
     (`deploy-snap4`) was blank; snap5 should fix it. Load the public URL and
     confirm the login screen renders.
  2. **Push `main` to GitHub** — local `main` (`e7113ee`) is **ahead of origin**;
     `git push origin main` (normal, no force — history already clean).

---

## The CSP hardening (what shipped)

**Goal:** drop `unsafe-eval` + script `unsafe-inline` + the unpkg CDN from the
production CSP. Kept `style-src 'unsafe-inline'` (React `style={{}}`, low risk).

**How:** `scripts/build_frontend.py` runs at **snapshot build time only** and:
- esbuild-transforms the 16 `text/babel` sources to plain **classic JSX** JS
  (transform, not bundle — preserves the global-`window.X`/load-order model),
- self-hosts **sha384-pinned** React/ReactDOM into `web/vendor/`,
- rewrites `index.html` to be Babel/unpkg-free (`rewrite_index_html`).
`backend/middleware/security_headers.py` emits the **strict CSP only when
`ENVIRONMENT=production`**; dev keeps the permissive policy so the live-Babel dev
workflow (`main`/`web/` unchanged) still works.

**Plan/spec:** `docs/superpowers/plans/2026-06-07-csp-hardening-jsx-precompile.md`.
Code-reviewed twice (sha384 pin + atomicity + re-pin recipe added from review).

### ⚠️ The 3-bug chain (hard-won — read before touching the build)

The precompiled frontend went blank **twice** before working, because the real
production serving path differs from a naive local static server:

1. **`const {…} = React` redeclaration.** Every component does a top-level
   `const { useState, … } = React;`. As separate **classic** scripts they share
   one global lexical scope → the 2nd+ `const` throws *"already declared"* and
   aborts that script → `App` never defined → blank. Babel's `text/babel` ran each
   script isolated, so it never collided.
   **Fix:** `transform_file` demotes that line to `var { … } = React;` (var lands
   on `window`, tolerates redeclaration). Commit `962ccae`.

2. **`.jsx` MIME + `nosniff`.** The precompiled files keep the `.jsx` extension and
   load as ordinary `<script src>`. StaticFiles served them as
   `application/octet-stream`; the security middleware sets
   `X-Content-Type-Options: nosniff`, so the browser **refused to execute** them →
   blank. (Old Babel *fetched* `.jsx` via XHR, so MIME never mattered.)
   **Fix:** `backend/main.py` registers `mimetypes.add_type("text/javascript",
   ".jsx")` before mounting StaticFiles. Commit `e7113ee` (in `deploy-snap5`).

**Lesson:** a plain `python -m http.server` does NOT send `nosniff` and sniffs
MIME, so it renders even when the real Space won't. **Verify renders against the
live Space (now public) or a server that sets `nosniff` + correct MIME — not a
bare static server.**

---

## Deploy mechanism (every redeploy)

The agent **cannot** push to the Space (safety classifier blocks whole-tree pushes
to external remotes) — the **user runs the force-push**. `main` is NOT pushable to
the Space directly (a 10.9 MB regular `disease_model.h5` lives in history → HF
rejects). So deploy via a **single-commit orphan snapshot**:

```bash
# from a clean main:
git checkout --orphan deploy-snapN
python scripts/build_frontend.py web          # precompile (MUST run; strict CSP needs it)
git lfs install --local
git lfs track "*.jpg" "*.pkl" "*.tflite" "*.onnx" "*.onnx.data" "*.npy" "*.h5" "backend/models/*.joblib"
git add .gitattributes; git add -A; git add --renormalize .
git add -f web/vendor backend/models/panns_head.joblib backend/models/yamnet_head.joblib
git commit -m "Deploy snapshot vN: ..."
# restore main (orphan checkout DELETES the gitignored joblibs — back them up first):
cp backend/models/*.joblib /tmp/ ; git checkout main ; cp /tmp/*.joblib backend/models/ ; git clean -fd web/vendor
```

Then the **user** force-pushes (new token `hf_Qwts…`):
```bash
git push --force "https://prajval007:<HF_WRITE_TOKEN>@huggingface.co/spaces/prajval007/smartcropadvisory" deploy-snapN:main
```

**Snapshot must-haves (verify before push):** `web/index.html` has 0
`text/babel`/`unpkg`; `app.jsx` has `var {…}=React` (not const); `backend/main.py`
has the `.jsx` mimetype line; `backend/models/panns_head.joblib` LFS oid =
`9bcbf3b…`; all model binaries are LFS pointers (~130 B).

## Space config (already set)

`ENVIRONMENT=production`, valid `FAST2SMS_API_KEY` (quick route, ₹5/SMS, ~₹70
wallet), `DEMO_PHONE=1234567890`, plus the 4 required secrets + ANTHROPIC/GEMINI/
OWM/VAPID. Visibility: **public** (flipped by user 2026-06-08).

## Auth model (live)

Phone+OTP. Demo number **`1234567890`** → on-screen code, no SMS, unlimited (use
for public demos/judges). Real numbers → real SMS (₹5 each), `demo_otp:null`,
5/hour per-IP. Magic `123456` and `demo_otp` are OFF in production
(see `docs/fast2sms-handoff-2026-06-07.md`).

---

## Verification (run after any deploy)

Public, so no token needed:
```bash
B=https://prajval007-smartcropadvisory.hf.space
curl -sI "$B/components/app.jsx" | grep -i content-type   # MUST be text/javascript (not octet-stream)
curl -s "$B/" | grep -c text/babel                         # 0
curl -sD- -o/dev/null "$B/" | grep -i content-security-policy | grep -o "script-src[^;]*"  # 'self'
```
**Render check (the one that matters):** load `$B/` in a browser, confirm the
KisanOS login card renders (not just the tea-field background). Probe:
`typeof window.App` should be `"function"`, `#root` should have children.
Demo login: phone `1234567890` → on-screen code → Sign in.

## Open / deferred

- [ ] **Verify `deploy-snap5` live render** (login card shows) — was `APP_STARTING`
      at handoff.
- [ ] **`git push origin main`** (main ahead of origin; normal push, history clean).
- [ ] HF token `hf_Qwts…` is in this session's transcript — rotate when done.
- [ ] Fast2SMS wallet top-up before heavy public traffic (₹5/real SMS).
- [ ] Leftover local branch `deploy-snap5` (deploy record) — delete if desired.

## Key files

`scripts/build_frontend.py`, `backend/main.py` (jsx mimetype + StaticFiles mount),
`backend/middleware/security_headers.py` (env-conditional CSP),
`tests/test_build_frontend.py`, `tests/test_security_headers.py`,
`docs/deploy/huggingface.md`.
