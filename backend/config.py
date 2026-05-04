"""
KisanOS Backend Configuration — pydantic-settings powered.
All secrets and tunables come from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "KisanOS API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # ── Authentication ───────────────────────────────────────────────────
    API_KEY: str = "kisanos-dev-key-change-in-production"

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["*"]

    # ── External API Keys ────────────────────────────────────────────────
    OWM_API_KEY: str = "bd5e378503939ddaee76f12ad7a97608"
    DATA_GOV_API_KEY: str = "579b464db66ec23bdd000001cdd3946e44ce4aab825747b0bc4f6e0d"
    NASA_FIRMS_KEY: str = "6a8dded48b9e7f3f8fb71ac4c5a45e89"

    # ── Model Paths ──────────────────────────────────────────────────────
    MODEL_DIR: str = os.path.dirname(os.path.abspath(__file__))
    CROP_MODEL_PATH: str = "crop_model.pkl"
    SCALER_PATH: str = "scaler.pkl"
    LABEL_ENCODER_PATH: str = "label_encoder.pkl"
    DISEASE_MODEL_TFLITE: str = "disease_model.tflite"
    DISEASE_MODEL_H5: str = "disease_model.h5"
    CLASS_NAMES_PATH: str = "class_names.npy"

    # ── Cache TTLs (seconds) ─────────────────────────────────────────────
    WEATHER_CACHE_TTL: int = 300       # 5 minutes
    FORECAST_CACHE_TTL: int = 1800     # 30 minutes
    FIRMS_CACHE_TTL: int = 600         # 10 minutes
    MARKET_CACHE_TTL: int = 900        # 15 minutes

    # ── Retry Config ─────────────────────────────────────────────────────
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_BASE: float = 0.5    # seconds

    def model_path(self, filename: str) -> str:
        """Resolve full path to a model file."""
        return os.path.join(self.MODEL_DIR, filename)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Singleton settings instance — cached after first call."""
    return Settings()
