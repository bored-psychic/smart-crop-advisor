"""
KisanOS FastAPI Backend — Main Application.
CORS-enabled, authenticated, with lifespan model loading.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import get_settings

logger = logging.getLogger("kisanos")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all ML models once at startup — zero cold-start on first request."""
    settings = get_settings()
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
        logger.info("  ✅ Acoustic model loaded (Random Forest, 8 classes)")
    except Exception as e:
        logger.warning(f"  ⚠️ Acoustic model unavailable: {e}")
        app.state.acoustic_model = None

    logger.info("🚀 KisanOS API ready!")
    yield
    logger.info("🛑 KisanOS API shutting down")


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

    # ── CORS — enabled for all origins during development ────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register routers ─────────────────────────────────────────────
    from backend.routers import crop, disease, market, irrigation, acoustic, field_watch

    app.include_router(crop.router)
    app.include_router(disease.router)
    app.include_router(market.router)
    app.include_router(irrigation.router)
    app.include_router(acoustic.router)
    app.include_router(field_watch.router)

    # ── Health check ─────────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    return app


# Application instance
app = create_app()
