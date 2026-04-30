from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL_WEATHER: int = 300  # 5 minutes
    CACHE_TTL_MARKET: int = 43200 # 12 hours
    WEATHER_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
