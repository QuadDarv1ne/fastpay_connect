"""Internationalization (i18n) middleware.

Automatically detects user's language preference and attaches it
to the request state for use throughout the application.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.utils.i18n import get_language_from_request, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE


class I18nMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic language detection and localization.

    Detects language from:
    1. Query parameter (?lang=en)
    2. Header (X-Language or Accept-Language)
    3. Cookie (language or lang)
    4. Default (ru)

    Sets request.state.language for downstream use.
    Adds Content-Language header to responses.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Detect language
        lang = get_language_from_request(request)

        # Attach to request state
        request.state.language = lang
        request.state.supported_languages = list(SUPPORTED_LANGUAGES)
        request.state.default_language = DEFAULT_LANGUAGE

        # Process request
        response = await call_next(request)

        # Add language header to response
        response.headers["Content-Language"] = lang

        # Add available languages header for client discovery
        response.headers["X-Available-Languages"] = ",".join(SUPPORTED_LANGUAGES)

        return response
