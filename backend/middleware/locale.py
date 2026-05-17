"""LocaleMiddleware — reads Accept-Language, picks first supported language,
stashes the two-letter code on request.state.lang. Defaults to 'en'."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.services.i18n.langs import is_supported


def _parse_accept_language(header: str | None) -> str:
    if not header:
        return "en"
    for raw in header.split(","):
        tag = raw.split(";", 1)[0].strip().lower()
        if not tag:
            continue
        primary = tag.split("-", 1)[0]
        if is_supported(primary):
            return primary
    return "en"


class LocaleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.lang = _parse_accept_language(request.headers.get("accept-language"))
        return await call_next(request)
