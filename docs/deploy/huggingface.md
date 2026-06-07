# Deploying KisanOS to Hugging Face Spaces

Operator runbook for hosting the full KisanOS app (FastAPI API + static `web/`
frontend) as a single Docker-based Hugging Face Space, with the **PANNs CNN14**
acoustic classifier running live.

---

## Locked decisions

- **Platform:** Hugging Face Spaces, **Docker SDK** (Firebase Hosting / Vercel /
  Netlify can't run FastAPI; HF runs the whole container). Cloud Run is the
  documented production-grade alternative — the Dockerfile honors `$PORT`, so it
  ports there with no changes.
- **ML tier: Full (C).** torch + torchaudio + panns-inference (PANNs live) +
  TensorFlow (disease TFLite). Image ≈ 4 GB.
- **Data: demo-grade.** SQLite `kisanos.db` is ephemeral on HF — it resets on
  every restart/sleep. No persistent disk, no external DB. Accepted for a demo.

## Image overview

- `Dockerfile` — `python:3.10.12-slim`; installs **CPU-only** torch/torchaudio
  from `https://download.pytorch.org/whl/cpu` (avoids the multi-GB CUDA build),
  then the rest of `requirements.txt`; pre-fetches the 312 MB CNN14 checkpoint at
  build time into `~/panns_data/`; runs as non-root `user`; starts
  `uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}`.
- `.dockerignore` — excludes `venv/`, `__pycache__/`, `.git/`, `.env*` (keeps
  `.env.example`), `kisanos.db`, `data/embeddings_cache/`, `tests/`.
- `README.md` — HF front-matter (`sdk: docker`, `app_port: 7860`).

## torch pin note (Devil OODA D2)

`torch==2.11.0` / `torchaudio==2.11.0` were confirmed present on the CPU wheel
index on 2026-06-06:

```bash
pip index versions torch --index-url https://download.pytorch.org/whl/cpu
# -> 2.12.0, 2.11.0, 2.10.0, ...
```

If a future rebuild fails because the pin disappeared, bump both to the newest
CPU pair the index lists and note the substitution here.

---

## Required Space Secrets

Set in **Space → Settings → Variables and secrets** (as *Secrets*, not
Variables). Boot **crash-loops** if any of the first four are missing
(`backend/config.py` → `get_settings()` raises → `lifespan` raises RuntimeError):

| Secret | Required | Notes |
|---|---|---|
| `API_KEY` | ✅ | Shared secret for service routes. |
| `JWT_SECRET` | ✅ | HS256 signing key. |
| `APP_PEPPER` | ✅ | Mixed into phone-number hashes. |
| `FERNET_KEY` | ✅ | PII encryption key — generate below. |
| `ANTHROPIC_API_KEY` | optional | Enables Claude soil/acoustic narratives. |
| `GEMINI_API_KEY` | optional | Acoustic fallback. |
| `OWM_API_KEY` | optional | Weather / irrigation. |
| `DATA_GOV_API_KEY` | optional | Agmarknet market prices. |
| `NASA_FIRMS_KEY` | optional | Field-watch fire alerts. |
| `FAST2SMS_API_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY` | optional | Alert delivery / web push. |

Generate a real Fernet key:

```bash
python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

---

## Local Docker runtime (macOS, via Colima)

Docker Desktop is not required. This repo was built/tested with Colima:

```bash
brew install colima docker
colima start --cpu 4 --memory 8 --disk 80
docker info        # confirm the daemon (colima context)
```

Note: Apple-Silicon Colima builds **arm64**; HF builds **amd64** from the same
Dockerfile. The local build validates Dockerfile logic + PANNs wiring; HF does
the authoritative amd64 build.

## Local smoke test

```bash
docker build -t kisanos-hf .

docker run --rm -p 7860:7860 \
  -e API_KEY=localtest \
  -e JWT_SECRET=localtestjwtsecret \
  -e APP_PEPPER=localtestpepper \
  -e FERNET_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
  kisanos-hf
```

Verify (the positive signal — not just HTTP 200):

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:7860/        # 200
SAMPLE=$(find tests data -iname '*.wav' | head -1)
curl -s -X POST http://localhost:7860/acoustic/analyze \
  -H "X-API-Key: localtest" -F "file=@${SAMPLE}" | grep -o '"analysis_method":"[a-z]*"'
# expect: "analysis_method":"panns"   (NOT the API fallback)
```

Startup logs must show PANNs loaded — **not** the
`⚠️ PANNs unavailable, acoustic pipeline will use API fallback` line
(`backend/main.py:100`).

---

## Create the Space and push

1. Create a write token: https://huggingface.co/settings/tokens
2. New Space: https://huggingface.co/new-space → SDK **Docker** (blank),
   hardware **CPU basic (free)**. Note `https://huggingface.co/spaces/<user>/<space>`.
3. Add the Secrets above.
4. The 14 MB `panns_head.joblib` exceeds HF's 10 MB non-LFS limit → track via LFS,
   then push `main` to the Space remote:

```bash
git lfs install
git lfs track "backend/models/*.joblib"
git add .gitattributes backend/models/panns_head.joblib
git commit -m "build: track PANNs head via git LFS for HF push"
git remote add space https://huggingface.co/spaces/<user>/<space>
git push space main
```

5. Watch **Logs**: models loaded, PANNs loaded (no fallback warning), uvicorn on
   `0.0.0.0:7860`. Then verify live:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://<user>-<space>.hf.space/   # 200
```

Open the URL, confirm the UI renders and an acoustic upload returns
`analysis_method: panns`.

---

## Snapshot-time frontend build (strict production CSP)

The production CSP (`ENVIRONMENT=production`) drops `unsafe-eval`, script
`unsafe-inline`, and the unpkg allowance. That only works because the deployed
frontend is **precompiled** — no in-browser Babel. So when building the deploy
snapshot, after the snapshot's `web/` is checked out and **before `git add -A`**,
run the frontend build:

```bash
# Precompile JSX + self-host React so the strict prod CSP can be applied.
# Runs on the orphan deploy branch ONLY; main/web stays live-Babel source.
.venv/bin/python scripts/build_frontend.py web

# web/ is now Babel-free and has web/vendor/ (both are gitignored), so force-add
# the generated vendor dir into the snapshot:
git add -f web/vendor
```

This step is part of building `deploy-snapN`; **never run it on `main`** (it
mutates `web/` in place). If you build a snapshot without it while
`ENVIRONMENT=production`, the strict CSP will block the still-Babel frontend and
the SPA won't load.

---

## Cold starts / paid upgrade

torch + TF + CNN14 give a ~30–60 s cold start, and the free Space sleeps after
~48 h idle. To keep it warm: **Settings → Hardware → CPU upgrade (~$0.03/hr)**
(a user/payment action), then Factory rebuild.

## Rollback

- Revert the bad commit and re-push: `git revert <sha> && git push space main`.
- Or in the Space UI: **Settings → Factory rebuild**, or pin a previous commit.

## Data caveat

The demo DB is ephemeral — users, alert subscriptions, and uploaded feedback
clips are **wiped on every restart/sleep**. For persistence, attach HF persistent
storage (~$5/mo) and point `SQLITE_PATH` at it, or migrate to a managed DB
(future cycle).
