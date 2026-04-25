"""
KisanOS API Authentication — API Key based.
All endpoints require a valid X-API-Key header.
"""

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from backend.config import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str:
    """
    FastAPI dependency that validates the API key.
    Raises 401 if missing, 403 if invalid.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    if api_key != get_settings().API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return api_key
