"""SecurityHeadersMiddleware — adds HTTP security headers to every response."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to all HTTP responses.

    Headers applied:
    - X-Content-Type-Options: nosniff — blocks MIME type sniffing attacks
    - X-Frame-Options: DENY — prevents clickjacking by forbidding framing
    - Referrer-Policy: strict-origin-when-cross-origin — controls referrer leakage
    - Strict-Transport-Security (HTTPS only) — enforces HTTPS; skipped on http for dev
    - Content-Security-Policy — restricts resource loading and inline script execution
      (unsafe-inline is a pragmatic starting point for React bundles; tighten once
      inline scripts are eliminated via bundler/module federation)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Always applied headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS only on HTTPS (skip on http for local dev)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Content-Security-Policy: pragmatic for React bundle with inline styles/scripts
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'"
        )

        return response
