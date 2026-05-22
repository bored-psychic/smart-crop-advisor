"""
KisanOS Backend Configuration — pydantic-settings powered.
All secrets and tunables come from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "KisanOS API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # "development" or "production"

    # ── Authentication ───────────────────────────────────────────────────
    # API_KEY: shared secret for service-to-service routes (kept after
    # T3 user-auth rollout — see backend/auth.py).
    API_KEY: str
    # JWT_SECRET: HS256 signing key for per-user tokens issued by /auth/*.
    # No default — boot must fail if missing (same pattern as API_KEY).
    JWT_SECRET: str
    JWT_TTL_HOURS: int = 24
    OTP_TTL_SECONDS: int = 300
    OTP_MAX_ATTEMPTS: int = 5

    # ── PII Encryption (P1 Task 3) ──────────────────────────────────────
    # APP_PEPPER: secret string mixed into the SHA-256 of phone numbers
    # before they're stored in alert_subscriptions / webpush_subscriptions
    # as `phone_hash`. The pepper is what makes the hash non-trivially
    # reversible from a stolen DB — without it, every phone number in
    # the world could be precomputed in minutes.
    # FERNET_KEY: base64url-encoded Fernet symmetric key used to encrypt
    # the phone number itself (phone_ciphertext column) and feedback
    # audio clips on disk. Decrypt-on-read so the API can still surface
    # the user's own phone back to them.
    # Both are REQUIRED — boot must fail if missing.
    APP_PEPPER: str
    FERNET_KEY: str

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── External API Keys ────────────────────────────────────────────────
    OWM_API_KEY: str = ""
    DATA_GOV_API_KEY: str = ""
    NASA_FIRMS_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # ── Model Paths ──────────────────────────────────────────────────────
    MODEL_DIR: str = os.path.dirname(os.path.abspath(__file__))
    CROP_MODEL_PATH: str = "crop_model.pkl"
    SCALER_PATH: str = "scaler.pkl"
    LABEL_ENCODER_PATH: str = "label_encoder.pkl"
    DISEASE_MODEL_TFLITE: str = "disease_model.tflite"
    DISEASE_MODEL_H5: str = "disease_model.h5"
    CLASS_NAMES_PATH: str = "class_names.npy"

    # ── Upload Limits ────────────────────────────────────────────────────
    MAX_IMAGE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # ── Redis Configuration ─────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # ── Cache TTLs (seconds) ─────────────────────────────────────────────
    WEATHER_CACHE_TTL: int = 300       # 5 minutes
    FORECAST_CACHE_TTL: int = 1800     # 30 minutes
    FIRMS_CACHE_TTL: int = 600         # 10 minutes
    MARKET_CACHE_TTL: int = 900        # 15 minutes

    # ── Retry Config ─────────────────────────────────────────────────────
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_BASE: float = 0.5    # seconds

    # Alert System
    FAST2SMS_API_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_EMAIL: str = "mailto:admin@kisanos.app"
    SQLITE_PATH: str = "kisanos.db"
    ALERT_CHECK_INTERVAL_HOURS: int = 6

    def model_path(self, filename: str) -> str:
        """Resolve full path to a model file."""
        return os.path.join(self.MODEL_DIR, filename)

    class Config:
        env_file = str(Path(__file__).parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Singleton settings instance — cached after first call."""
    return Settings()
