"""Request ID Middleware.

Generates or extracts a unique request ID for each incoming request and
propagates it via response headers and the request state. This enables
request tracing across logs, error reports, and downstream services.
"""

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that ensures every request has a unique X-Request-ID."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Use client-provided ID if present, otherwise generate one
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex

        # Store on request state so it can be accessed by handlers and log filters
        request.state.request_id = request_id

        response = await call_next(request)

        # Propagate the ID back in the response
        response.headers[REQUEST_ID_HEADER] = request_id

        return response
