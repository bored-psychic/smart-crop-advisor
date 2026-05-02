from pydantic_settings import BaseSettings
from typing import Optional
import os

_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

class Settings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL_WEATHER: int = 300
    CACHE_TTL_MARKET: int = 43200
    WEATHER_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    class Config:
        env_file = os.path.join(_ROOT, ".env")

settings = Settings()
