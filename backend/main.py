"""
KisanOS FastAPI Backend — Main Application.
CORS-enabled, authenticated, with lifespan model loading.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import ValidationError
from backend.config import get_settings
from backend.middleware.locale import LocaleMiddleware
from backend.services.db import init_db
from backend.services.alerts import check_and_send_alerts
from backend.routers import subscriptions as subscriptions_router

logger = logging.getLogger("kisanos")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all ML models once at startup — zero cold-start on first request."""
    _scheduler = None
    try:
        settings = get_settings()
    except ValidationError as e:
        logger.error(
            "❌ API_KEY env var is required. "
            "Set API_KEY environment variable and restart."
        )
        raise RuntimeError(
            "API_KEY env var is required. "
            "Set API_KEY environment variable and restart."
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

    # ── CORS ─────────────────────────────────────────────────────────
    # Header-based auth (X-API-Key) doesn't require allow_credentials.
    # For production, restrict allow_origins to specific frontend domains.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── LocaleMiddleware ─────────────────────────────────────────────
    # Parses Accept-Language header and attaches request.state.lang
    app.add_middleware(LocaleMiddleware)

    # ── Register routers ─────────────────────────────────────────────
    from backend.routers import crop, disease, market, irrigation, acoustic, field_watch, soil, dosage

    app.include_router(crop.router)
    app.include_router(disease.router)
    app.include_router(market.router)
    app.include_router(irrigation.router)
    app.include_router(acoustic.router)
    app.include_router(field_watch.router)
    app.include_router(soil.router)
    app.include_router(dosage.router)
    app.include_router(subscriptions_router.router)

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
