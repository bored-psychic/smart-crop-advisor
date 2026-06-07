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

        # HSTS only on HTTPS (skip on plain http for local dev). Behind a
        # TLS-terminating proxy (e.g. HF Spaces) the app sees http, so trust
        # the X-Forwarded-Proto the edge sets to detect the real scheme.
        forwarded_proto = request.headers.get(
            "x-forwarded-proto", request.url.scheme
        ).split(",")[0].strip()
        if forwarded_proto == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Content-Security-Policy. Production serves a PRECOMPILED frontend
        # (scripts/build_frontend.py) so we drop 'unsafe-eval', script
        # 'unsafe-inline' and the unpkg CDN. Dev keeps the permissive policy the
        # in-browser Babel SPA needs. style-src keeps 'unsafe-inline' in both for
        # React style={{}} props (low XSS risk) + Google Fonts.
        from backend.config import get_settings
        if get_settings().is_production:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "img-src 'self' data:; "
                "media-src 'self' blob:; "
                "connect-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "img-src 'self' data:; "
                "media-src 'self' blob:; "
                "connect-src 'self' https://unpkg.com; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com"
            )

        return response
