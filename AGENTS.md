# KisanOS — Smart Crop Advisory System

AI-powered crop advisory for Indian farmers. FastAPI backend (:8000),
Streamlit frontend (:8501), legacy React UI (`web/`). ML via Scikit-learn,
Prophet, optionally TensorFlow. Bioacoustic analysis via Anthropic API.

## Before writing ANY code
1. **Verify, don't assume.** `ls`, `grep`, read the file. If you haven't read it, you don't know what's in it.
2. **Never invent imports.** Grep the codebase for `Y` before writing `from X import Y`.
3. **Never fabricate paths.** Run `ls` — the filesystem is the source of truth.
4. **Never invent endpoints.** Read `backend/main.py` and the relevant `backend/routers/` file first.
5. **Never guess artifact names.** Run `ls backend/*.pkl backend/*.h5 backend/*.tflite backend/*.npy`.
6. **Check `requirements.txt` before using any import.** Single shared file at project root.

Do not modify code until you can state the exact file+line, every downstream
consumer (grepped), and a runnable validation command. If you can't, ask.

Bug reports are not fix orders — reproduce first, then wait for go-ahead.

## Key gotchas
- **Python 3.10.12** — pinned. TF 2.13 breaks on 3.12, Prophet on 3.11+.
- **`numpy<1.24.0`** — Prophet hard requirement. Upgrading silently corrupts price forecasts.
- **TensorFlow is optional** — not in `requirements.txt`. When absent, disease detection uses `_hsv_analysis()` in `backend/services/vision.py` (NumPy HSV color analysis). This is a real, intentional fallback — not a bug.
- **Two config files**: `backend/config.py` (new services) and `backend/core/config.py` (original). See `.env.example` for which vars go where.
- **Schema changes break the frontend silently.** Grep `frontend/` before touching `backend/schemas/*.py`.
- **ModelManager returns `None` on missing artifacts.** Endpoints must handle this and return 503.
- **Cache keys use `str(args)`** — pass only primitives to avoid non-deterministic keys.
- **`/web` is legacy** — bug fixes only. No npm, no build steps. New features go in Streamlit.
- **Model artifacts are read-only.** Never retrain, move, or rename `.pkl`/`.h5`/`.tflite`/`.npy` files.
- **`--host 0.0.0.0`** on uvicorn is intentional (Docker/LAN). Do not change to `127.0.0.1`.

## Run locally
```
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000
streamlit run frontend/app.py --server.port 8501
```

## Validate after changes
```
curl http://localhost:8000/health
# Check http://localhost:8000/docs and http://localhost:8501
```

## Code style
PEP 8, 100 char lines, type hints on public functions, Pydantic schemas for
all API responses. No formatters (Black/Ruff). No test framework unless asked.

## Git
Conventional Commits (`feat:`, `fix:`, `refactor:`). Branch prefixes: `feat/`, `fix/`, `chore/`.
Never commit `.env`, `*.pkl`, `*.h5`, `*.tflite`, `*.npy`, `__pycache__/`, `venv/`.

## Anthropic API
Use model ID `Codex-sonnet-4-6` for any new code touching the bioacoustic feature.
