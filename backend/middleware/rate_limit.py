"""
slowapi rate-limit configuration for KisanOS.

Key strategy
------------
- Authenticated routes (disease/analyze-image, acoustic/analyze,
  alerts/subscribe): keyed on ``request.state.user["sub"]`` — the
  phone-hash JWT sub set by ``require_user``.  User-level keys are not
  bypassable through shared NAT or VPNs the way IP keys are.
- Unauthenticated OTP route (auth/request-otp): keyed on the submitted
  phone number stored in ``request.state.otp_phone`` by the
  ``_otp_phone_dep`` dependency (which must appear before the limiter
  fires).  Falls back to remote IP if the phone is not present.

Usage
-----
Import ``limiter`` into the router module and decorate the endpoint::

    from backend.middleware.rate_limit import limiter
    from fastapi import Request

    @router.post("/your-route")
    @limiter.limit("20/hour")
    async def your_route(request: Request, ...):
        ...

The ``request`` parameter **must** appear in the function signature for
slowapi to inject the limit correctly.

For the OTP route, also add ``_otp_phone_dep`` as a dependency so the
phone is stored in ``request.state`` before the limiter key function
runs::

    from backend.middleware.rate_limit import limiter, _otp_rate_limit_key

    @router.post("/request-otp")
    @limiter.limit("5/hour", key_func=_otp_rate_limit_key)
    async def request_otp(
        request: Request,
        body: RequestOtpBody,
        _phone_for_limit: None = Depends(_otp_phone_dep),
        ...
    ):
        ...

Wire-up in main.py (already done in create_app)::

    from slowapi.errors import RateLimitExceeded
    from backend.middleware.rate_limit import limiter

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, <custom_429_handler>)
"""

from __future__ import annotations

import re

from starlette.requests import Request
from slowapi import Limiter

from backend.config import get_settings

_DIGITS = re.compile(r"\D+")


def _loose_normalise(raw: str) -> str:
    """Collapse a phone string to ``+<digits>`` (default +91), non-raising.

    Mirrors ``auth._normalise_phone`` for the 10-digit / country-code cases so
    the demo-number comparison in the key function is consistent. Returns ``""``
    for empty/garbage input (callers treat that as "no phone").
    """
    digits = _DIGITS.sub("", raw or "")
    if len(digits) == 10:
        digits = "91" + digits
    return "+" + digits if digits else ""


async def _otp_phone_dep(request: Request) -> None:
    """Stash the request's normalised phone on ``request.state`` *before* the
    slowapi limiter fires, so the key function can exempt the demo number.

    Runs as a FastAPI dependency — resolved before slowapi's wrapper performs
    the limit check. Reads the cached JSON body (Starlette caches it, so the
    route's own ``body: RequestOtpBody`` parsing is unaffected).
    """
    try:
        data = await request.json()
        raw = data.get("phone", "") if isinstance(data, dict) else ""
    except Exception:
        raw = ""
    request.state.otp_phone = _loose_normalise(raw)


def _ip_fallback(request: Request) -> str:
    """Extract the best available remote IP from the request."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return f"ip:{forwarded_for.split(',')[0].strip()}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


def _rate_limit_key(request: Request) -> str:
    """
    Return the rate-limit bucket key for the incoming request.

    Priority:
    1. Authenticated user sub (JWT claims stored by ``require_user``).
       This is the preferred key — not bypassable via shared NAT.
    2. Remote IP address fallback (for any route where user auth has
       not yet run or is intentionally absent).

    slowapi calls this function after FastAPI's dependency injection for
    the route has resolved (it is injected as an additional dependency).
    This means ``require_user`` has already populated
    ``request.state.user`` by the time this key function fires for all
    authenticated endpoints.
    """
    # 1. JWT-authenticated user — preferred.
    user = getattr(request.state, "user", None)
    if isinstance(user, dict):
        sub = user.get("sub")
        if sub:
            return f"user:{sub}"

    # 2. Remote IP fallback.
    return _ip_fallback(request)


def _otp_rate_limit_key(request: Request) -> str:
    """
    Key function for the /auth/request-otp endpoint.

    Returns an **empty string** for the dedicated ``DEMO_PHONE`` — slowapi
    treats a falsy key as "no limit" and skips throttling entirely, so the
    demo login is never rate-limited.

    For every other request it returns the remote-IP bucket (the historical,
    intentionally coarse behaviour: per-IP, not per-phone, so a sender can't
    dodge the limit by cycling phone numbers). ``request.state.otp_phone`` is
    populated by ``_otp_phone_dep`` before the limiter fires.
    """
    phone = getattr(request.state, "otp_phone", None)
    if phone and isinstance(phone, str):
        demo = get_settings().DEMO_PHONE
        if demo and phone == _loose_normalise(demo):
            return ""  # exempt the demo number from rate limiting
    return _ip_fallback(request)


limiter = Limiter(key_func=_rate_limit_key)
