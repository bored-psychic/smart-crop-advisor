"""
KisanOS API Authentication.

Two dependencies are exported here:

- ``require_api_key`` — shared-secret guard for *service-to-service* routes
  (cron triggers, internal alert worker calls, etc.). Checks
  ``X-API-Key`` header against ``settings.API_KEY``.

- ``require_user`` — per-user guard for routes called from the browser.
  Validates a signed JWT in the ``Authorization: Bearer <token>`` header,
  issued by ``/auth/verify-otp``. Returns the decoded claims dict so
  handlers can read ``request.state.user`` style data (sub = phone_hash,
  phone = E.164 string).

The two are intentionally separate — the browser must NEVER hold the
service-to-service API key (that was Task 3).
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

import jwt
from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from backend.config import get_settings

# ─── Service-to-service API key ────────────────────────────────────────
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str:
    """
    FastAPI dependency that validates the service-to-service API key.

    Reserved for internal/cron/admin routes. The browser frontend must
    use ``require_user`` instead — see module docstring.
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


# ─── Per-user JWT auth ─────────────────────────────────────────────────
_bearer_scheme = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"


def hash_phone(phone: str) -> str:
    """
    Stable, non-reversible identifier for a phone number.

    SHA-256 over the normalised E.164 string. Used both as the JWT
    ``sub`` claim and as the row key in ``auth_otps``. The salt is *not*
    included here — this is a deterministic identifier, not a credential
    hash. (OTP hashes use a per-row salt; see backend/services/auth.py.)
    """
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


def issue_token(phone: str) -> tuple[str, int]:
    """
    Mint a JWT for the given phone number. Returns ``(token, exp_unix)``.
    """
    settings = get_settings()
    now = int(time.time())
    exp = now + settings.JWT_TTL_HOURS * 3600
    claims = {
        "sub": hash_phone(phone),
        "phone": phone,
        "iat": now,
        "exp": exp,
        "jti": hashlib.sha256(f"{phone}:{now}".encode()).hexdigest()[:16],
    }
    token = jwt.encode(claims, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, exp


def decode_token(token: str) -> dict[str, Any]:
    """
    Validate a JWT and return its claims. Raises HTTP 401 on failure.

    Wraps PyJWT's exception family into a single 401 response so callers
    don't have to import jwt.exceptions.
    """
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from e


async def require_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
) -> dict[str, Any]:
    """
    FastAPI dependency that validates the bearer JWT and returns claims.

    Side effect: stashes claims onto ``request.state.user`` so downstream
    handlers (e.g. ``/alerts/history`` in Task 6) can read
    ``request.state.user["sub"]`` without redeclaring the dependency.
    """
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = decode_token(creds.credentials)
    request.state.user = claims
    return claims


# ─── Dual-mode auth (JWT for SPA, API key for cron/service callers) ──
async def require_user_or_api_key(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
    api_key: str | None = Security(_api_key_header),
) -> dict[str, Any]:
    """
    Accept either a per-user JWT or the service-to-service API key.

    Used for routes that are called from BOTH the SPA (JWT) and cron
    workers / scheduled jobs (API key). Prefers the JWT when present
    so user context is preserved; falls back to API-key validation
    otherwise.

    Returns the JWT claims dict when authed via JWT, or a sentinel
    ``{"sub": "service", "auth": "api_key"}`` when authed via API key,
    so handlers can branch on ``claims.get("auth") == "api_key"`` if
    they need to (most won't).
    """
    # Prefer JWT if a bearer credential is present.
    if creds is not None and creds.credentials:
        claims = decode_token(creds.credentials)
        request.state.user = claims
        return claims

    # Fall through to API key.
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer token or X-API-Key header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if api_key != get_settings().API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    service_claims = {"sub": "service", "auth": "api_key"}
    request.state.user = service_claims
    return service_claims
