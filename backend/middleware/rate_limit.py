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
    @limiter.limit("3/hour", key_func=_otp_rate_limit_key)
    async def request_otp(
        request: Request,
        body: RequestOtpBody,
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

from starlette.requests import Request
from slowapi import Limiter


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

    Keys on ``request.state.otp_phone`` (set by FastAPI's body parsing
    when the route parameter ``body: RequestOtpBody`` is resolved — the
    phone value is stored there by the route handler before the limiter
    fires in the same dependency chain).

    Falls back to IP if the phone is not yet available.

    Note: In practice, FastAPI resolves all route parameters (including
    Pydantic body models) before slowapi's injected dependency runs, so
    ``request.state.otp_phone`` is available here for the OTP route.
    The route handler must call::

        request.state.otp_phone = _normalise_phone(body.phone)

    at the top of its body to populate this field for the key function.
    Since slowapi hooks into the route as a *post-parameter* dependency,
    the body parameters are parsed first, giving the handler time to set
    the state.

    We achieve this by storing the phone at the start of the route
    function body; however since the limiter dependency fires *after*
    the body is parsed but potentially *before* the handler body runs,
    we use a ``Depends``-based approach: the route declares
    ``_phone_for_limit=Depends(_otp_phone_dep)`` which runs first and
    sets the state. See ``_otp_phone_dep`` below.
    """
    phone = getattr(request.state, "otp_phone", None)
    if phone and isinstance(phone, str):
        return f"phone:{phone.strip()}"
    return _ip_fallback(request)


limiter = Limiter(key_func=_rate_limit_key)
