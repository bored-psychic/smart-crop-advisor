"""
KisanOS FastAPI Backend — Main Application.
CORS-enabled, authenticated, with lifespan model loading.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import ValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from backend.config import get_settings
from backend.middleware.locale import LocaleMiddleware
from backend.middleware.security_headers import SecurityHeadersMiddleware
from backend.middleware.rate_limit import limiter
from backend.schemas.errors import ErrorResponse
from backend.services.db import init_db
from backend.services.alerts import check_and_send_alerts
from backend.routers import subscriptions as subscriptions_router
from backend.routers import auth as auth_router

logger = logging.getLogger("kisanos")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all ML models once at startup — zero cold-start on first request."""
    _scheduler = None
    try:
        settings = get_settings()
    except ValidationError as e:
        logger.error(
            "❌ Required env vars missing (API_KEY, JWT_SECRET). "
            "Set them in .env and restart."
        )
        raise RuntimeError(
            "Required env vars missing (API_KEY, JWT_SECRET). "
            "Set them in .env and restart."
        ) from e

    logger.info("🌾 KisanOS API starting — loading ML models...")

    from backend.ml import crop_model, disease_model, price_model, acoustic_model

    try:
        app.state.crop_model = crop_model.load()
        logger.info("  ✅ Crop model loaded (Random Forest)")
    except Exception as e:
        logger.warning(f"  ⚠️ Crop model unavailable: {e}")
        app.state.crop_model = None

    try:
        app.state.disease_model = disease_model.load()
        logger.info("  ✅ Disease model loaded (TFLite/HSV)")
        # Warmup: dummy forward pass to JIT-compile the graph.
        try:
            import numpy as _np
            from PIL import Image as _Image
            _dummy = _Image.fromarray(_np.zeros((224, 224, 3), dtype=_np.uint8))
            app.state.disease_model.predict_from_image(_dummy)
            logger.info("  🔥 Disease model warmed")
        except Exception as _e:
            logger.warning(f"  ⚠️ Disease warmup skipped: {_e}")
    except Exception as e:
        logger.warning(f"  ⚠️ Disease model unavailable: {e}")
        app.state.disease_model = None

    try:
        app.state.price_models = price_model.load_all()
        logger.info(f"  ✅ Price models loaded ({len(app.state.price_models)} crops)")
    except Exception as e:
        logger.warning(f"  ⚠️ Price models unavailable: {e}")
        app.state.price_models = {}

    try:
        app.state.acoustic_model = acoustic_model.load()
        n_classes = len(getattr(app.state.acoustic_model, "classes", []) or [])
        logger.info(f"  ✅ Acoustic model loaded (PANNs CNN14, {n_classes} classes)")
        # Warmup: 1 s of silence at 32 kHz (CNN14 input rate) to prime the
        # forward pass. Abstain on silence is expected — we only care that
        # the embedding path executes without error.
        try:
            import numpy as _np
            _silence = _np.zeros(32000, dtype=_np.float32)
            try:
                app.state.acoustic_model.predict(_silence, 32000, crop_type="warmup")
            except Exception:
                pass  # abstain on silence is fine; the forward pass ran
            logger.info("  🔥 PANNs CNN14 warmed")
        except Exception as _e:
            logger.warning(f"  ⚠️ PANNs warmup skipped: {_e}")
    except Exception as e:
        logger.warning(
            f"  ⚠️ PANNs unavailable, acoustic pipeline will use API fallback: {e}"
        )
        app.state.acoustic_model = None

    # Startup probe for YAMNet (secondary fallback, not loaded into app state).
    # This sets yamnet_model.MODEL_AVAILABLE so the pipeline 503 guard is accurate.
    try:
        from backend.ml import yamnet_model as _yamnet_module
        _yamnet_module.load()
        logger.info("  ✅ YAMNet head available (secondary fallback)")
    except Exception as _e:
        logger.info(f"  ℹ️ YAMNet unavailable (expected if only PANNs is trained): {_e}")

    # Alert system — DB tables + scheduled checker
    await init_db()
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        check_and_send_alerts,
        "interval",
        hours=get_settings().ALERT_CHECK_INTERVAL_HOURS,
        id="alert_check",
    )
    _scheduler.start()

    logger.info("🚀 KisanOS API ready!")
    yield
    logger.info("🛑 KisanOS API shutting down")
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI-powered crop advisory API for Indian farmers. "
            "Provides crop recommendation, disease detection, market forecasting, "
            "irrigation advice, acoustic pest detection, and satellite field watch."
        ),
        lifespan=lifespan,
    )

    # ── Rate limiting (slowapi) ───────────────────────────────────────
    # limiter is keyed on JWT sub (user) or phone (OTP route) or remote IP.
    app.state.limiter = limiter

    async def _rate_limited_json(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        """Return a structured 429 with retry_after in seconds."""
        # slowapi stores the limit detail on the exception; extract retry delay
        # from the Retry-After header that slowapi would normally set.
        retry_after: int = 3600  # conservative default (1 hour)
        try:
            # exc.detail is e.g. "5 per 1 hour" — parse the window
            parts = str(exc.detail).split()
            # typical: "5 per 1 hour"
            if len(parts) >= 4 and parts[1] == "per":
                count = int(parts[2])
                unit = parts[3].rstrip("s")  # "hour" / "minute"
                if unit == "hour":
                    retry_after = 3600
                elif unit == "minute":
                    retry_after = 60
        except Exception:
            pass
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limited", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    app.add_exception_handler(RateLimitExceeded, _rate_limited_json)

    # ── Unified HTTPException → ErrorResponse handler ─────────────────
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Convert every HTTPException to the canonical ErrorResponse shape.

        Sites that already pass a dict with a ``code`` key (e.g. T8's
        ``{"code": "model_unavailable", ...}``) are forwarded as-is.
        Plain-string detail values get a snake_case code derived from the
        HTTP status phrase (e.g. 404 → ``not_found``).
        """
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            payload = ErrorResponse(
                code=exc.detail["code"],
                message=exc.detail.get("message", str(exc.detail)),
                detail=(
                    {k: v for k, v in exc.detail.items() if k not in ("code", "message")}
                    or None
                ),
            )
        else:
            import http
            code = http.HTTPStatus(exc.status_code).phrase.lower().replace(" ", "_")
            payload = ErrorResponse(code=code, message=str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    # ── CORS ─────────────────────────────────────────────────────────
    # Token-based auth (Authorization: Bearer) doesn't require allow_credentials.
    # allow_origins is controlled via CORS_ORIGINS env var (dev default: localhost:5173, localhost:3000).
    # allow_methods and allow_headers restricted to what the frontend actually uses.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # ── SecurityHeadersMiddleware ────────────────────────────────────
    # Adds HTTP security headers (X-Content-Type-Options, X-Frame-Options,
    # Referrer-Policy, HSTS, CSP) to every response.
    app.add_middleware(SecurityHeadersMiddleware)

    # ── LocaleMiddleware ─────────────────────────────────────────────
    # Parses Accept-Language header and attaches request.state.lang
    app.add_middleware(LocaleMiddleware)

    # ── Register routers ─────────────────────────────────────────────
    from backend.routers import crop, disease, market, irrigation, acoustic, field_watch, soil, dosage, geo

    app.include_router(crop.router)
    app.include_router(disease.router)
    app.include_router(market.router)
    app.include_router(irrigation.router)
    app.include_router(acoustic.router)
    app.include_router(field_watch.router)
    app.include_router(soil.router)
    app.include_router(dosage.router)
    app.include_router(subscriptions_router.router)
    app.include_router(auth_router.router)
    app.include_router(geo.router)

    # ── Health check ─────────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    WEB_DIR = Path(__file__).parent.parent / "web"
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")

    return app


# Application instance
app = create_app()
